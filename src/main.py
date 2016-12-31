#!/usr/bin/env python
# encoding: utf-8

try:
    import pygtk
    pygtk.require("2.0")
except Exception:
    pass

import gtk
import cv2
import StringIO
import traceback
import sys
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.relpath(__file__))


class Window(object):

    def __init__(self):
        self.__build = gtk.Builder()
        self.__build.add_from_file(os.path.join(BASE_DIR, "ui.glade"))
        self.__build.connect_signals(self)

        self.__orgin_im = None
        self.__im = None

        self.window = self.__build.get_object("window")
        self.image = self.__build.get_object("image_main")

        self.text_method = self.__build.get_object("entry_method")
        self.text_script = self.__build.get_object("textview_script").get_buffer()
        self.text_parameters = self.__build.get_object("textview_parameters").get_buffer()
        self.text_output = self.__build.get_object("textview_output").get_buffer()

    def _choose_file(self, *args):
        dialog = gtk.FileChooserDialog(
            'Open Image',
            self.window,
            gtk.FILE_CHOOSER_ACTION_OPEN,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)
        )
        dialog.set_select_multiple(False)
        response = dialog.run()
        if response == gtk.RESPONSE_ACCEPT.real:
            filename = dialog.get_filename()
            im = cv2.imread(filename)
            if im is not None:
                self.__im = im
                self.__orgin_im = np.copy(im)
                self._show_image()
        dialog.destroy()

    def _save_file(self, *args):
        dialog = gtk.FileChooserDialog(
            'Save Image',
            self.window,
            gtk.FILE_CHOOSER_ACTION_SAVE,
            (gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT,
             gtk.STOCK_OK, gtk.RESPONSE_ACCEPT)
        )
        dialog.set_select_multiple(False)
        response = dialog.run()
        if response == gtk.RESPONSE_ACCEPT.real and self.__im is not None:
            filename = dialog.get_filename()
            try:
                cv2.imwrite(filename, self.__im)
            except Exception as e:
                print(e)
        dialog.destroy()

    def _reset_image(self, *args):
        if self.__orgin_im is not None:
            self.__im = np.copy(self.__orgin_im)
        self._show_image()

    def _exec_method(self, *args):
        self.__exec_method()

    def _exec_and_apply_method(self, *args):
        self.__exec_method(True)

    def __exec_method(self, override=False):
        self.text_output.set_text('')
        if self.__im is None:
            self.text_output.set_text('Error: Image has not loaded')
            return

        is_advanced = self.__build.get_object('togglebutton_advanced').get_active()

        if override:
            im = self.__im
        else:
            im = np.copy(self.__im)

        global_ctx = {
            'cv2': cv2,
            'np': np,
            'numpy': np,
            'os': os
        }
        local_ctx = {
            'im': im
        }

        if is_advanced:
            # exec multi lines script
            script = self.text_script.get_text(
                self.text_script.get_start_iter(),
                self.text_script.get_end_iter()
            )
            try:
                exec(script, global_ctx, local_ctx)
                self._show_image(im)
            except Exception as e:
                self.text_output.set_text(self.collect_exception(e))
            return

        # exec a single method
        method = self.text_method.get_text().strip()
        parameters = self.text_parameters.get_text(
            self.text_parameters.get_start_iter(),
            self.text_parameters.get_end_iter()
        )
        if not method:
            self.text_output.set_text("Error: method is empty")
            return

        if method not in dir(cv2):
            self.text_output.set_text("Error: method '%s' is not exists" % (method))
            return

        func = cv2.__getattribute__(method)
        try:
            args = eval('[%s]' % (parameters), global_ctx, local_ctx)
            new_im = func(im, *args) or im
            if override and new_im is not None:
                self.__im = new_im
            self._show_image(new_im)
        except Exception as e:
            self.text_output.set_text(self.collect_exception(e))

    def on_image_button_release_event(self, widget, event):
        print "on_image_button_release_event"
        print event.type, event.x, event.y

    def on_advanced_toggled(self, widget):
        container1 = self.__build.get_object("vbox_script")
        container2 = self.__build.get_object("vbox_method")
        if widget.get_active():
            container1.show_all()
            container2.hide_all()
        else:
            container1.hide_all()
            container2.show_all()

    def main_quit(self, *args):
        gtk.main_quit()

    def _show_image(self, img=None):
        """
        Refresh Image
        """
        if img is None:
            img = self.__im

        if img is None:
            return

        ret, im = cv2.imencode('.ppm', img)
        if not ret:
            return
        contents = im.tostring()

        loader = gtk.gdk.PixbufLoader("pnm")
        loader.write(contents, len(contents))
        pixbuf = loader.get_pixbuf()
        loader.close()

        self.image.set_from_pixbuf(pixbuf)
        self.image.set_size_request(640, 480)

    def start(self):
        self.window.show_all()
        self.__build.get_object("vbox_script").hide_all()
        gtk.main()

    def collect_exception(self, e):
        f = StringIO.StringIO()
        traceback.print_exception(type(e), e, sys.exc_traceback, file=f)
        contents = f.getvalue()
        if isinstance(contents, unicode):
            contents = contents.encode('utf8')
        return contents


if __name__ == '__main__':
    win = Window()
    win.start()
