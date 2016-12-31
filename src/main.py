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
import time
import numpy as np

BASE_DIR = os.path.dirname(os.path.relpath(__file__))


class Window(object):

    def __init__(self):
        self.__build = gtk.Builder()
        self.__build.add_from_file(os.path.join(BASE_DIR, "ui.glade"))
        self.__build.connect_signals(self)

        self.__orgin_im = None
        self.__im = None
        self.__im_scale = 1

        self.window = self.__build.get_object("window")
        self.image = self.__build.get_object("image_main")
        self.box = self.__build.get_object("eventbox1")

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
                self.__im_scale = 1
                self._show_image()
                self._enable_buttons()
                self.update_status_bar("")
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
        x = event.x / self.__im_scale
        y = event.y / self.__im_scale
        self.update_status_bar("Clicked Point: (%s, %s)" % (x, y))

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

    def on_button_zoom_actual_clicked(self, *args):
        if self.__im_scale != 1:
            self.__im_scale = 1
            self._show_image()
        self.update_status_bar("")

    def on_button_zoom_in_clicked(self, *args):
        if self.__im_scale >= 3:
            return

        self.__im_scale += 0.05
        self._show_image()
        self.update_status_bar("")

    def on_button_zoom_out_clicked(self, *args):
        scale = self.__im_scale - 0.05
        if scale <= 0:
            return

        w, h = self.parse_image_size(self.__im)
        if (w*scale) < 10 or (h*scale) < 50:
            return

        self.__im_scale = scale
        self._show_image()
        self.update_status_bar("")

    def update_status_bar(self, text):
        self.__build.get_object("statusbar1").push(
            int(time.time()),
            "Zoom: %s%% %s" % (self.__im_scale * 100, text)
        )

    def _show_image(self, img=None, scale=None):
        """
        Refresh Image
        """
        if img is None:
            img = self.__im
        if img is None:
            return

        if scale is None:
            scale = self.__im_scale
        if scale != 1:
            img = cv2.resize(img, (0, 0), fx=scale, fy=scale)

        ret, im = cv2.imencode('.ppm', img)
        if not ret:
            return
        contents = im.tostring()

        loader = gtk.gdk.PixbufLoader("pnm")
        loader.write(contents, len(contents))
        pixbuf = loader.get_pixbuf()
        loader.close()

        self.image.set_from_pixbuf(pixbuf)
        w, h = self.parse_image_size(img)
        self.box.set_size_request(w, h)
        self.image.set_size_request(w, h)

    def _enable_buttons(self):
        self.__build.get_object("button_save").set_sensitive(True)
        self.__build.get_object("button_reset").set_sensitive(True)
        self.__build.get_object("button_zoom_in").set_sensitive(True)
        self.__build.get_object("button_zoom_out").set_sensitive(True)
        self.__build.get_object("button_zoom_actual").set_sensitive(True)
        self.__build.get_object("button_exec").set_sensitive(True)
        self.__build.get_object("button_apply").set_sensitive(True)

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

    def parse_image_size(self, img):
        if len(img.shape) > 2:
            # shape: (rows|height, cols|width, color)
            _, w, h = img.shape[::-1]
        else:
            # shape: (rows|height, cols|width)
            w, h = img.shape[::-1]

        return (w, h)


if __name__ == '__main__':
    win = Window()
    win.start()
