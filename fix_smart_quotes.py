# fix_smart_quotes.py
import pathlib

p = pathlib.Path(r"C:\Users\tyler\Desktop\FoundersSOManager\models.py")

# Read with Windows-1252 to safely decode curly quotes/dashes
s = p.read_text(encoding="cp1252", errors="strict")

# Normalize curly quotes/dashes to ASCII
trans = {
    0x2018:"'", 0x2019:"'", 0x201A:"'", 0x2032:"'", 0x2035:"'",  # single quotes/prime
    0x201C:'"', 0x201D:'"', 0x201E:'"', 0x2033:'"', 0x2036:'"',  # double quotes
    0x2013:"-", 0x2014:"-", 0x2212:"-",                          # dashes/minus
}
s = s.translate(trans)

# Ensure UTF-8 coding cookie at top
header = "# -*- coding: utf-8 -*-\n"
if not s.lstrip().startswith(header):
    s = header + s

# Write back as UTF-8
p.write_text(s, encoding="utf-8", newline="\n")
print("models.py normalized to UTF-8 and saved.")
# coderabbit-review-marker
