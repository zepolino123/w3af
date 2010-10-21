"""
httpeditor.py

Copyright 2008 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
import gtk
import pango
import os
import sys

try:
    import gtksourceview2 as gtksourceview
except Exception, e:
    print e
    sys.exit()

from core.data.constants import severity
from core.ui.gtkUi.entries import Searchable

SEVERITY_TO_COLOR={
    severity.INFORMATION: 'green',
    severity.LOW: 'blue',
    severity.MEDIUM: 'yellow',
    severity.HIGH: 'red'}
SEVERITY_TO_COLOR.setdefault('yellow')

class HttpEditor(gtk.VBox, Searchable):
    """Special class for editing HTTP requests/responses."""
    def __init__(self):
        gtk.VBox.__init__(self)
        self.is_request = True
        # Create the textview where the text is going to be shown
        self.textView = gtksourceview.View(gtksourceview.Buffer())
        self.textView.set_highlight_current_line(True)
        self.textView.set_show_line_numbers(True)
        self.textView.set_wrap_mode(gtk.WRAP_WORD)
        self.textView.set_border_width(5)
        fontDesc = pango.FontDescription('monospace')
        if fontDesc:
            self.textView.modify_font(fontDesc)

        lm = gtksourceview.LanguageManager()
        foo = lm.get_search_path()
        foo.append('core' + os.path.sep+ 'ui' + os.path.sep + 'gtkUi')
        lm.set_search_path(foo)
        lang = lm.get_language('http')

        b = self.textView.get_buffer()
        b.set_language(lang)
        b.set_highlight_syntax(True)

        self.reset_bg_color()
        for sev in SEVERITY_TO_COLOR:
            self.textView.get_buffer().create_tag(sev, background=SEVERITY_TO_COLOR[sev])
        self.textView.show()
        # Scroll where the textView goes
        sw1 = gtk.ScrolledWindow()
        sw1.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        sw1.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw1.add(self.textView)
        sw1.show()
        self.pack_start(sw1, expand=True, fill=True)
        # Create the search widget
        Searchable.__init__(self, self.textView, small=True)
# 
# Interface
#
    def clear(self):
        buf = self.textView.get_buffer()
        start, end = buf.get_bounds()
        buf.delete(start, end)

    def get_text(self, splitted=False):
        buf = self.textView.get_buffer()
        rawText = buf.get_text(buf.get_start_iter(), buf.get_end_iter())
        if not splitted:
            return rawText
        # else return turple headers+data
        headers = rawText
        data = ""
        tmp = rawText.find("\n\n")
        # It's POST!
        if tmp != -1:
            headers = rawText[0:tmp+1]
            data = rawText[tmp+2:]
            if data.strip() == "":
                data = ""
        return (headers, data)

    def set_text(self, text, fixUtf8=False):
        buf = self.textView.get_buffer()
        if fixUtf8:
            buf.set_text(text)
        else:
            buf.set_text(text)

    def set_editable(self, e):
        return self.textView.set_editable(e)

    def highlight(self, text, sev=severity.MEDIUM):
        """Find the text, and handle highlight.
        @return: None
        """
        text_buffer = self.textView.get_buffer()

        (ini, fin) = text_buffer.get_bounds()
        alltext = text_buffer.get_text(ini, fin)
        # find the positions where the phrase is found
        positions = []
        pos = 0
        while True:
            try:
                pos = alltext.index(text, pos)
            except ValueError:
                break
            fin = pos + len(text)
            iterini = text_buffer.get_iter_at_offset(pos)
            iterfin = text_buffer.get_iter_at_offset(fin)
            positions.append((pos, fin, iterini, iterfin))
            pos += 1
        # highlight them all
        for (ini, fin, iterini, iterfin) in positions:
            text_buffer.apply_tag_by_name(sev, iterini, iterfin)

# 
# Inherit SourceView methods
#
    def set_highlight_current_line(self, val):
        self.textView.set_highlight_current_line(val)

    def set_show_line_numbers(self, val):
        self.textView.set_show_line_numbers(val)

    def set_wrap_mode(val):
        self.textView.set_wrap_mode(val)
# 
# Private methods
#
    def _to_utf8(self, text):
        """
        This method was added to fix:

        GtkWarning: gtk_text_buffer_emit_insert: assertion `g_utf8_validate (text, len, NULL)'

        @parameter text: A text that may or may not be in UTF-8.
        @return: A text, that's in UTF-8, and can be printed in a text view
        """
        text = repr(text)
        text = text[1:-1]

        for special_char in ['\n', '\r', '\t']:
            text = text.replace( repr(special_char)[1:-1], special_char )
        text = text.replace("\\'", "'")
        text = text.replace('\\\\"', '\\"')
        return text

    def get_iter_at_offset(self, position):
        return self.textView.get_buffer().get_iter_at_offset(position)

    def apply_tag_by_name(self, tag, start, end):
        return self.textView.get_buffer().apply_tag_by_name(tag, start, end)


    def set_border_width(self, b):
        return self.textView.set_border_width(b)

    def set_bg_color(self, color):
        self.textView.modify_base(gtk.STATE_NORMAL, color)

    def reset_bg_color(self):
        self.textView.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))

    def get_buffer(self):
        return self.textView.get_buffer()

