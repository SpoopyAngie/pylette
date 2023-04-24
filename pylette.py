#!/usr/bin/python3

from argparse import ArgumentParser as argumentparser
from pathlib import Path as path
from PIL import Image as image, ImageColor as imagecolor
import multiprocessing
import yaml
from random import uniform
from math import sqrt

def colordifference(color_a, color_b):
    return sqrt((color_a[0] - color_b[0])**2 + (color_a[1] - color_b[1])**2 + (color_a[2] - color_b[2])**2)

def process(input_image, pixel_start_index, chunk_size, color_palette, pixel_randomizer, queue):
    while pixel_start_index.value < input_image.size[0] * input_image.size[1]:
        with pixel_start_index.get_lock():
            pixel_index_chunk = pixel_start_index.value
            pixel_start_index.value += chunk_size

        chunk = []
        for pixel_index in range(pixel_index_chunk, min(pixel_index_chunk + chunk_size, input_image.size[0] * input_image.size[1])):
            pixel_x = pixel_index % input_image.size[0]
            pixel_y = int(pixel_index / input_image.size[0])
            
            palette_difference = 500
            pixel_palette = None
            pixel_palette_second = None
            for pallete_color in color_palette:
                pallete_color_difference  = colordifference(input_image.getpixel((pixel_x, pixel_y)), pallete_color)
                pallete_color_difference *= 1 - uniform(-pixel_randomizer, pixel_randomizer)

                if pallete_color_difference < palette_difference:
                    palette_difference = pallete_color_difference
                    pixel_palette_second = pixel_palette
                    pixel_palette = pallete_color
            chunk.append(((pixel_x, pixel_y), pixel_palette))
        queue.put(chunk)

def thread(chunk, image):
    for pixel in chunk: image.putpixel(*pixel)

if __name__ == '__main__':
    chunk_size = 128**2
    
    parser = argumentparser()
    parser.add_argument('image', help='Path of input image file', type=path)
    parser.add_argument('-o', '--output', help='Path of output image file', type=path)
    parser.add_argument('-p', '--palette', help='Path of color palette YAML file', required=True, type=path)
    arguments = parser.parse_args()

    with open(arguments.palette) as color_palette_file:
        color_palette_yml = yaml.load(color_palette_file, Loader=yaml.FullLoader)
        color_palette = []
        for color_palette_hex in color_palette_yml.values():
            if color_palette_hex[0] == '#' and len(color_palette_hex) == 7: color_palette.append(imagecolor.getrgb(color_palette_hex))
        color_palette = tuple(color_palette)

    with image.open(arguments.image).convert('RGB') as input_image:
        process_queue = multiprocessing.Queue()
        process_arguments = (input_image, multiprocessing.Value('i'), chunk_size, color_palette, pixel_randomizer, process_queue,)

        process_list = [multiprocessing.Process(target = process, args = process_arguments) for _ in range(multiprocessing.cpu_count())]
        for process in process_list: process.start()

        with image.new('RGB', input_image.size) as output_image:
            for process in process_list:
                while process.is_alive():
                    if not process_queue.empty():
                        for pixel in process_queue.get():
                            output_image.putpixel(*pixel)

            output_image.save(arguments.output or input("Output file path: "))