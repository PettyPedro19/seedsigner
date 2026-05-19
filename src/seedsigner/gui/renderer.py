from PIL import Image, ImageDraw
from threading import Lock

from seedsigner.emulator.desktopDisplay import desktopDisplay
from seedsigner.models.singleton import ConfigurableSingleton

# Hardcoded display config for BitPolito fork (Pi Zero = ST7789 240x240)
DISPLAY_TYPE__ST7789 = "st7789"
DISPLAY_TYPE__ILI9341 = "ili9341"
DISPLAY_TYPE__ILI9486 = "ili9486"

ALL_DISPLAY_TYPES = [DISPLAY_TYPE__ST7789, DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486]

DEFAULT_DISPLAY_TYPE   = DISPLAY_TYPE__ST7789
DEFAULT_DISPLAY_WIDTH  = 240
DEFAULT_DISPLAY_HEIGHT = 320    # It was 240, changed to 320 in order to get 'portrait' shape in the bigger display version.


class Renderer(ConfigurableSingleton):
    buttons = None
    canvas_width = 0
    canvas_height = 0
    canvas: Image.Image = None
    draw: ImageDraw.ImageDraw = None
    disp = None
    lock = Lock()
    is_screenshot_generator = False  # required by newer SeedSigner screensaver code


    @classmethod
    def configure_instance(cls):
        renderer = cls.__new__(cls)
        cls._instance = renderer
        renderer.initialize_display()


    def initialize_display(self):
        self.lock.acquire()

        # BitPolito fork does not have SETTING__DISPLAY_CONFIGURATION;
        # hardcode ST7789 240x240 which matches the target hardware.
        self.display_type = DEFAULT_DISPLAY_TYPE
        width  = DEFAULT_DISPLAY_WIDTH
        height = DEFAULT_DISPLAY_HEIGHT

        if self.disp is None:
            self.disp = desktopDisplay(self.display_type, width=width, height=height)
        else:
            self.disp.display_type = self.display_type
            self.disp.width  = width
            self.disp.height = height
            self.disp.update_geometry()

        if self.display_type == DISPLAY_TYPE__ST7789:
            self.canvas_width  = self.disp.width
            self.canvas_height = self.disp.height
        elif self.display_type in [DISPLAY_TYPE__ILI9341, DISPLAY_TYPE__ILI9486]:
            self.canvas_width  = self.disp.height
            self.canvas_height = self.disp.width

        self.canvas = Image.new('RGB', (self.canvas_width, self.canvas_height))
        self.draw   = ImageDraw.Draw(self.canvas)

        self.lock.release()


    def show_image(self, image=None, alpha_overlay=None, show_direct=False):
        if show_direct:
            self.disp.ShowImage(image, 0, 0)
            return

        if alpha_overlay:
            if image is None:
                image = self.canvas
            image = Image.alpha_composite(image, alpha_overlay)

        if image:
            self.canvas.paste(image)

        self.disp.ShowImage(self.canvas, 0, 0)


    def show_image_pan(self, image, start_x, start_y, end_x, end_y, rate, alpha_overlay=None):
        cur_x = start_x
        cur_y = start_y
        rate_x = rate
        rate_y = rate
        if end_x - start_x < 0:
            rate_x *= -1
        if end_y - start_y < 0:
            rate_y *= -1

        while (cur_x != end_x or cur_y != end_y) and (rate_x != 0 or rate_y != 0):
            cur_x += rate_x
            if (rate_x > 0 and cur_x > end_x) or (rate_x < 0 and cur_x < end_x):
                cur_x -= rate_x
                rate_x = 0

            cur_y += rate_y
            if (rate_y > 0 and cur_y > end_y) or (rate_y < 0 and cur_y < end_y):
                cur_y -= rate_y
                rate_y = 0

            crop = image.crop((cur_x, cur_y, cur_x + self.canvas_width, cur_y + self.canvas_height))

            if alpha_overlay:
                crop = Image.alpha_composite(crop, alpha_overlay)

            self.canvas.paste(crop)
            self.disp.ShowImage(crop, 0, 0)


    def display_blank_screen(self):
        self.draw.rectangle((0, 0, self.canvas_width, self.canvas_height), outline=0, fill=0)
        self.show_image()
