
"""
Simple stock price scraping, with calculation over them
Using basic python libs, avoid installs, simple scraping. Would be easier with yfinance for example (Yahoo Finance API)
see config.json :
List of stock (config: stocks ["",""], default ["CYBR","PANW"])
Interval (config: interval_minutes, deafalt 1)
Calculation (Config: calculation), Any calculation which can use the sock ticker names as variables, default "(PANW * 2.2005 + 45) - CYBR"

Iterate over multiple scarpers to avoid being bloked.
Right click context: Refresh/Font/Show hide After Houres prices/Exit 
""" 
import urllib.request
import requests
import re
import json
import tkinter as tk
import threading
from datetime import datetime
import gzip
from tkinter import font
import time
import zlib
import random

# Define Scaper sources.
class BaseScraper:
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Pragma": "no-cache",
            "Connection": "keep-alive"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def fetch_url(self, url, context = None):
        try:
            req = urllib.request.Request(url, headers=self.headers)
            start = time.perf_counter()
            with urllib.request.urlopen(req, timeout=self.timeout, context = context) as resp:
                print(f"Request took: {(time.perf_counter() - start):.3f}s, ", end="")
                data = resp.read()
                elapsed = time.perf_counter() - start
                print(f"{elapsed:.3f}s")
                encoding = resp.getheader("Content-Encoding")

                if encoding == "gzip":
                    data = gzip.decompress(data)
                elif encoding == "deflate":
                    data = zlib.decompress(data)  # deflate fallback

                html = data.decode("utf-8", errors="ignore")
                #with open("html_output.html", "w", encoding="utf-8") as ho:
                #    ho.write(html)
                print(url)
                return html
        except Exception as e:
            print(f"[ERROR] Failed to fetch URL {url}: {e}")
            return None
    
    def fetch_url_requests(self, url):
        try:
            print(f"Request to {url}")
            start_total = time.perf_counter()
            resp = self.session.get(url, timeout=self.timeout, stream=True)
            start_read = time.perf_counter()
            data = resp.raw.read()
            end_read = time.perf_counter()
            elapsed_handshake = start_read - start_total
            elapsed_total = end_read - start_total

            print(f"Handshake + headers: {elapsed_handshake:.3f}s, total download: {elapsed_total:.3f}s")

            encoding = resp.headers.get("Content-Encoding")
            if encoding == "gzip":
                data = gzip.decompress(data)
            elif encoding == "deflate":
                data = zlib.decompress(data)

            html = data.decode("utf-8", errors="ignore")
            return html

        except Exception as e:
            print(f"[ERROR] Failed to fetch URL {url}: {e}")
            return None

class GoogleScraper(BaseScraper):
    def get_price(self, ticker):
        html = self.fetch_url_requests(f"https://www.google.com/finance/quote/{ticker}:NASDAQ")
        value = None
        value_faterh = None
        if html:
            match_afterh = re.search(r'After Hours:.*?\$([\d.]+)<', html, re.DOTALL)
            match = re.search(r'data-last-price="([\d.]+)"', html)
            if match:
                value =  float(match.group(1))
            if match_afterh:
                value_faterh = float(match_afterh.group(1).replace(',', ''))
            else:
                value_faterh = value
        return value, value_faterh

class MarketWatchScraper(BaseScraper):
    def get_price(self, ticker):
        html = self.fetch_url_requests(f"https://www.marketwatch.com/investing/stock/{ticker}")
        value = None
        value_faterh = None
        if html:
            match_afterh = re.search(r'<bg-quote class="value"[^>]*>([\d.,]+)</bg-quote>', html) # after hours
            match = re.search(r'<meta name="price" content="\$([^"]+)" />', html)
            if match:
                value = float(match.group(1).replace(',', ''))
            if match_afterh:
                value_faterh = float(match_afterh.group(1).replace(',', ''))
            else:
                value_faterh = value
        return value, value_faterh

# List of supported scrapers
Scrapers = [MarketWatchScraper(), GoogleScraper()]
Colors = ["lime", "cyan", "white", "green", "pink", "orange"]

class StockWidget(tk.Tk):
    def __init__(self, config):
        super().__init__()

        # Read config, with defaults per entry
        self.stocks = config.get("stocks", ["CYBR", "PANW"])
        self.interval = config.get("interval_minutes", 1)
        if not type(self.interval) == int or self.interval <= 0:
            self.interval = 1
        self.calc_expr = config.get("calculation", "(PANW * 2.2005 + 45) - CYBR")
        print(self.stocks)
        print(self.interval)
        print(self.calc_expr)
        self.scrapers = Scrapers # Will iterate over list of scarpers using different one in each cycle
        self.scraper_index = 0
        self.after_houres_visable = True # Status of After houres price\calc, start as visable
        self.maximized = True

        # GUI setup
        # Remove title bar & make window always on top (fyi, in Windows this means you have no snapping)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        # Set background & padding
        self.configure(bg="black")
        #Font size and font family setting and tracking
        self.font_size = 12
        self.preferred_fonts = ["Consolas", "Courier New", "Monospace", "Verdana"]
        self.font_index = 0

        # Go over font list, find the first usable font and remove any non available fonts from the list
        self.label_font = None
        for f in self.preferred_fonts[:]: # Ietrate over copy so we can modify the original
            try:
                if not self.label_font:
                    # The first available one is made the active used font
                    self.label_font = font.Font(family=f, size=self.font_size)
                font.Font(family=f, size=self.font_size)
            except tk.TclError:
                # Font not available, remove it from list
                self.font_index += 1
                self.preferred_fonts.remove[f]
        
        # Create labels
        self.prices = {}        # Price variables, ticker to price dictinary, 
        self.prices_afterh = {} # After houres price variables, ticker to price dictinary
        self.labels_afterh = [] # TK labels list for labels used to present After Houres price only.
        ticker_color_index = 0 
        # Build variables and Labels per Tickers
        for ticker in self.stocks:
            var = tk.StringVar(value=f"{ticker}: --")
            color = Colors[ticker_color_index]
            tk.Label(self, textvariable=var, fg=color, bg="black", font=self.label_font).pack(anchor="w", padx=5, pady=0)
            var_afterh = tk.StringVar(value=f"-- ")
            label = tk.Label(self, textvariable=var_afterh, fg=color, bg="black", font=("Consolas", 8))
            label.pack(anchor="e", padx=5, pady=0)
            self.labels_afterh.append(label)
            ticker_color_index = (ticker_color_index + 1) % len(Colors)
            self.prices[ticker] = var
            self.prices_afterh[ticker] = var_afterh
        
        # Variable and Labels for the calculation
        self.calc_var = tk.StringVar(value="~Δ  : --")
        self.calc_label = tk.Label(self, textvariable=self.calc_var, fg="yellow", bg="black", font=self.label_font)
        self.calc_label.pack(anchor="w", padx=5, pady=0)
        self.calc_var_afterh = tk.StringVar(value=" -- ")
        label = tk.Label(self, textvariable=self.calc_var_afterh, fg="yellow", bg="black", font=("Consolas", 8, "bold"))
        label.pack(anchor="e", padx=5, pady=0)
        self.labels_afterh.append(label)

        # Backup packing info, to allow hide(unpack) and restore(pack) the layout.
        self.lbackup = []
        for widget in self.winfo_children():
            if isinstance(widget, tk.Label):
                self.lbackup.append(widget.pack_info())
        
        # Allow dragging window with mouse
        self.bind("<Button-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

        # Create right-click context menu
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="↺ Refresh", command=self.manual_refresh)
        self.context_menu.add_command(label="↑ Font", command=self.font_up)
        self.context_menu.add_command(label="↓ Font ", command=self.font_down)
        self.context_menu.add_command(label="→ Next Font", command=self.font_next)
        self.context_menu.add_command(label="↩ Font reset", command=self.font_reset)
        self.context_menu.add_command(label="⚪ Toggle Afterh", command=self.toggle_after_houres)
        
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Exit", command=self.destroy)

        # Bind right-click to show menu
        self.bind("<Button-3>", self.show_context_menu)

        # Windows: <Control-MouseWheel> with font+/font- as zoomin zoomout
        self.bind("<Control-MouseWheel>", lambda e: self.font_up(e) if e.delta > 0 else self.font_down(e))

        # Linux: <Control-Button-4> (scroll up), <Control-Button-5> (scroll down)
        self.bind("<Control-Button-4>", self.font_up)
        self.bind("<Control-Button-5>", self.font_down)

        self.bind("<Double-Button-1>", self.min_max)

        # Start update loop
        self.after(0, self.update_prices)

    def start_move(self, event):
        self._x = event.x
        self._y = event.y

    def do_move(self, event):
        x = event.x_root - self._x
        y = event.y_root - self._y
        self.geometry(f"+{x}+{y}")
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        self.context_menu.tk_popup(event.x_root, event.y_root)
    
    def next_scraper(self):
        scraper = self.scrapers[self.scraper_index]
        self.scraper_index = (self.scraper_index + 1)%len(self.scrapers)
        return scraper

    def fetch_prices_thread(self, scraper, schedule_next=True):
        """ Worker thread to fetch prices
        """
        prices = {}
        prices_afterh={}
        now = datetime.now()
        print(now)
        for ticker in self.stocks:
            price, price_afteth = scraper.get_price(ticker)
            if price is None:
                price = 0.0  # fallback if failed
                price_afteth = 0.0
            prices[ticker] = price
            prices_afterh[ticker] = price_afteth
            print(f"{ticker} : {price}, {price_afteth}")

        # Schedule GUI update in main thread
        self.after(0, self.update_gui, prices, prices_afterh, schedule_next)
    
    def update_gui(self, prices, prices_afterh, schedule_next):
        updare_err = False
        # Update prices
        for ticker, price in prices.items():
            if price == 0:
                # Failed to update, mark result as old, but keep the previous
                old_price = self.prices[ticker].get()
                try:
                    prices[ticker] = float(old_price[len(ticker) + 2:]) # Override with previous
                    self.prices[ticker].set(old_price.replace(" ","*",1))
                except:
                    updare_err = True
                    break
            else:
                self.prices[ticker].set(f"{ticker}: {price:.2f}")
            
            if prices_afterh[ticker] == 0:
                old_price = self.prices_afterh[ticker].get()
                prices_afterh[ticker] = float(old_price) # Override with previous
            else:
                self.prices_afterh[ticker].set(f"{prices_afterh[ticker]:.2f}")

        # Evaluate calculation
        if not updare_err:
            try:
                result = eval(self.calc_expr, {}, prices)
                self.calc_var.set(f"~Δ  : {result:.2f}")
                if result < 5:
                    self.blink_label_bg(self.calc_label)
                result = eval(self.calc_expr, {}, prices_afterh)
                self.calc_var_afterh.set(f"{result:.2f}")
            except:
                self.calc_var.set("~Δ  : !!error!!")
                self.calc_var_afterh.set("!!error!!")

        # Schedule next update
        if schedule_next:
            jitter_ms = int(random.uniform(10, 30) * 1000)
            self.after(self.interval * 60 * 1000 + jitter_ms, self.update_prices)
    
    def update_prices(self):
        """ Kick off fetch in thread to allow gui to stay responsive
        """
        scraper = self.next_scraper()
        threading.Thread(target=self.fetch_prices_thread, args=(scraper,), daemon=True).start()

    def manual_refresh(self):
        """Manual refresh (does NOT schedule next update)"""
        scraper = self.next_scraper()
        threading.Thread(target=self.fetch_prices_thread, args=(scraper, False), daemon=True).start()
    
    def toggle_after_houres(self):
        """ Hide all 'After Houres' prices\calculation Labels """
        if self.after_houres_visable:         
            for label in self.labels_afterh:
                label.pack_forget()
        else:
            i = 0
            for widget in self.winfo_children():
                if isinstance(widget, tk.Label):
                    widget.pack(**self.lbackup[i])
                    i+=1
        
        self.after_houres_visable = not self.after_houres_visable

    def min_max(self, event = None):
        if self.maximized:
            for widget in self.winfo_children():
                if isinstance(widget, tk.Label) and widget != self.calc_label:
                    widget.pack_forget()
        else:
            # Restore, should note the state of agter houres display
            i = 0
            for widget in self.winfo_children():
                if isinstance(widget, tk.Label):
                    if not self.after_houres_visable and widget in self.labels_afterh:
                        i+=1
                        continue
                    widget.pack(**self.lbackup[i])
                    i+=1

        self.maximized = not self.maximized

    def font_up(self, event = None):
        """ Increse Font size """
        if self.font_size <= 16:
            self.font_size +=1
            self.label_font.configure(size=self.font_size)

    def font_down(self, event = None):
        """ Decrese font size """
        if self.font_size > 8 :
            self.font_size -=1
            self.label_font.configure(size=self.font_size)
    
    def font_reset(self):
        """ Reset font size and family to defauls """
        self.font_size = 12
        self.font_index = 0
        self.label_font.configure(family=self.preferred_fonts[0], size=12)
    
    def font_next(self):
        """ Cycle through font list of available font families """
        self.font_index = (self.font_index + 1) % len(self.preferred_fonts)
        self.label_font.configure(family=self.preferred_fonts[self.font_index], size=self.font_size)
    
    def blink_label_bg(self, label, times=6, interval=300, color="red"):
        original_bg = label.cget("bg")
        def _toggle(count):
            if count > 0:
                # Toggle background color
                new_bg = color if label.cget("bg") == original_bg else original_bg
                label.config(bg=new_bg)
                self.after(interval, _toggle, count - 1)
            else:
                # Restore original background when done
                label.config(bg=original_bg)
        _toggle(times)

if __name__ == "__main__":
    # Load config
    try:
        with open("config.json") as f:
            config = json.load(f)
    except:
        print("Config file not found, using defaults!")
        config = {}

    StockWidget(config).mainloop()
