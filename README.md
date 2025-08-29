Simple quick stock price ticker widget. Intentially not using any extrenal lib.
Always on top, minimal, movable, scalable.
Basic scraping for stock after houres/during trading price.
Single line of calculation using the same ticker names.

Configuration (Config.json):
"stocks": [] # List of ticker names, examples: GOOG, CYBR, PANW
"interval_minutes": <int> # Update interval inminutes
"calculation": <str> # optional calculation using the ticker names. For example "(PANW \* 2.2005 + 45)" - CYBR.

Control:
1.Drag
2. CTRL+Mounse weel, inc\dec font size
3. Double click: toggle on\off view of calculation line only. Note that the line could just as well be one of the ticker names.

Rigght click menu:
 -Refresh : Manual value refresh
 -Font (inc) : Inc by 1 font size
 -Font (dec) : dec by 1 font size
 -Next Font : Iterate over suppoerted fonts
 -Font reset : Reset to startp size and type
 -Toggle Afterh : Toggle on\off after hour prices view
