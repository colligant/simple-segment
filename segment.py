import tkinter as tk
from collections import defaultdict, namedtuple
from json import dump, load
from os import remove
from os.path import splitext, basename, join, isfile
from glob import glob
from PIL import ImageTk, Image
from argparse import ArgumentParser

point = namedtuple('point', 'x y')

class SimpleSegment(object):

    def __init__(self, image_path, label_directory, image_extension="png", lambda_func=None):
        self.files = sorted(glob(join(image_path, "*" + image_extension)))
        self.label_directory = label_directory
        self.drawing = False
        self.object_ids = defaultdict(list)
        self.poly_coords = defaultdict(list)
        self.poly_count = 0
        self.image_index = 0
        self.save_on_next = True
        root = tk.Tk()
        self.canvas = tk.Canvas(root)
        self.canvas.old_coords = None
        self.canvas.pack(fill='both', expand='yes')
        self._draw_image(self.files[self.image_index])
        self.info_box = tk.StringVar()
        self._update_string()
        self.lr_label = tk.Label(root, textvariable=self.info_box)
        self.lr_label.place(relx=1.0, rely=1.0, anchor='se')
        root.bind('<Motion>', self._draw_polygon)
        root.bind('<Button-3>', self._not)
        root.bind('u', self._remove)
        root.bind('j', self._prev_image)
        root.bind('l', self._skip_100)
        root.bind('h', self._back_100)
        root.bind('k', self._next_image)
        root.bind('d', self._delete_json_file)
        root.mainloop()

    def _skip_100(self, event):
        self.image_index = min(len(self.files)-1, self.image_index + 100)
        self._draw_image(self.files[self.image_index])
        self._update_string()

    def _back_100(self, event):
        self.image_index = max(0, self.image_index - 100)
        self._draw_image(self.files[self.image_index])
        self._update_string()

    def _update_string(self):
        string_to_format = 'k: next image, j: prev image, h: skip 100 back. l: skip 100 forward. u: remove polygon. d: delete all labels. images: {} of {}'
        string = string_to_format.format(self.image_index+1, len(self.files))
        self.info_box.set(string)


    def _delete_json_file(self, event):
        json = self._create_json_filename(self.files[self.image_index])
        try:
            remove(json)
        except FileNotFoundError as e:
            print("Labels don't exist for this image")
        self.save_on_next = False

    def _draw_image(self, image_path):
        img = ImageTk.PhotoImage(Image.open(image_path))
        self.canvas.image = img
        self.canvas.create_image(0, 0, image=img, anchor='nw')

    def _create_json_filename(self, filename):
        out_filename = join(self.label_directory,
                splitext(basename(filename))[0]) + ".json"
        return out_filename
    
    def _dump_coord_dict(self):
        if not self.save_on_next:
            return
        out_filename = self._create_json_filename(self.files[self.image_index])
        with open(out_filename, 'w') as f:
            dump(self.poly_coords, f)
        self.object_ids = defaultdict(list)
        self.poly_coords = defaultdict(list)
        self.poly_count = 0

    def _next_image(self, event):
        if len(self.poly_coords):
            self._dump_coord_dict()
        self.image_index += 1
        if self.image_index > len(self.files) - 1:
            print("End of images!")
            return
        self._draw_image(self.files[self.image_index])
        self._load_and_draw_predrawn_polys(self.files[self.image_index])
        self._update_string()


    def _load_and_draw_predrawn_polys(self, image_filename):
        json_filename = self._create_json_filename(image_filename)
        if not isfile(json_filename):
            return
        with open(json_filename, 'r') as f:
            poly_coords = load(f)
        for poly_id in poly_coords:
            self.poly_count += 1 
            x1, y1 = poly_coords[poly_id][0], poly_coords[poly_id][1]
            for i, poly_coord in enumerate(poly_coords[poly_id][1:]):
                # reconstruct neccessary structures
                obj_id = self.canvas.create_line(poly_coord[0], poly_coord[1], x1, y1,
                        fill='red', width=2)
                x1, y1 = poly_coord[0], poly_coord[1]
                self.object_ids[self.poly_count].append(obj_id)
                self.poly_coords[self.poly_count].append(point(x=poly_coord[0], y=poly_coord[1]))

    def _prev_image(self, event):
        if self.image_index <= 0:
            print("Beginning of images!")
            return
        self.object_ids = defaultdict(list)
        self.poly_coords = defaultdict(list)
        self.poly_count = 0
        self.image_index -= 1
        self._draw_image(self.files[self.image_index])
        self._load_and_draw_predrawn_polys(self.files[self.image_index])
        self._update_string()

    def _not(self, event):
        if not self.drawing:
            self.canvas.old_coords = None
            self.drawing = True
            self.poly_count += 1
            self.save_on_next = True
        else:
            self.drawing = False
    
    def _remove(self, event):
        if self.poly_count == 0:
            return
        obj_ids = self.object_ids.pop(self.poly_count)
        self.poly_coords.pop(self.poly_count)
        for c in obj_ids:
            self.canvas.delete(c)
        self.poly_count -= 1

    def _draw_polygon(self, event):
        if self.drawing:
            x, y = event.x, event.y
            if self.canvas.old_coords:
                x1, y1 = self.canvas.old_coords
                obj_id = self.canvas.create_line(x, y, x1, y1, fill='red', width=2)
                self.object_ids[self.poly_count].append(obj_id)
                self.poly_coords[self.poly_count].append(point(x=x, y=y))
            self.canvas.old_coords = x, y

if __name__ == '__main__':
     ap = ArgumentParser()
     ap.add_argument('--image-directory', type=str, help='directory where the images are stored',
             required=True)
     ap.add_argument('--label-directory', type=str, help='directory to save JSON labels in',
             required=True)
     ap.add_argument('--image-extension', type=str, help='extension of images', default='png')
     args = ap.parse_args()
     SimpleSegment(args.image_directory, args.label_directory, image_extension=args.image_extension)
