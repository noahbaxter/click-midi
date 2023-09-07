import os
import sys
import shutil
import argparse
from pydub import AudioSegment

from PIL import Image, ImageFilter, ImageDraw

import charts_to_notes
import click_to_midi

AUDIO_FORMATS = [".mp3", ".ogg", ".wav", ".flac", ".aac"]
IMAGE_FORMATS = [".png", ".jpg"]

DIV_NUM_LINES = 80
VERBOSE = False

def main(input, output=''):
    
    in_files = [os.path.join(input, f) for f in os.listdir(input) if  os.path.isfile(os.path.join(input, f))]
    
    beat = ""
    audio = ""
    image = ""
    ini = ""
    instruments = []
    event = ""

    for file in in_files:
        f = os.path.basename(file.lower())
        
        if "beat" in os.path.splitext(f)[0] and any(f.endswith(ext) for ext in AUDIO_FORMATS + [".mid"]):
            if beat:
                if f.endswith(".mid") and not beat.endswith(".mid"):
                    beat = file # a beat midi file overrides a beat audio file, but only once
                else:
                    raise Exception("multiple beat files detected")
            beat = file
        elif any(f.endswith(ext) for ext in AUDIO_FORMATS):
            if audio:
              raise Exception("multiple track audio files detected")
            audio = file
        elif any(f.endswith(ext) for ext in IMAGE_FORMATS):
            if image:
              raise Exception("multiple images detected")
            image = file
        elif f.endswith("song.ini"):
            if ini:
              raise Exception("multiple ini detected")
            ini = file
        elif any(f.endswith(ext) for ext in [".mid", ".midi"]):
            if any(inst in f for inst in ["drum", "guitar", "bass"]):
                instruments += [file]
            elif any(_type in f for _type in ["event"]):
                event = file
        elif any(f.endswith(ext) for ext in [".ds_store"]):
            pass
        else:
            raise Exception(f"unknown file type '{file}'")

    if not output:
        output = os.path.join(
            os.path.dirname(input),
            "out"
        )
        output = os.path.join(output, os.path.splitext(os.path.basename(audio))[0])
    
    print("Generate song from following items:",
        f"\tBeat - '{beat}'",
        f"\tAudio - '{audio}'",
        f"\tInstruments - {instruments}",
        f"\tEvents - '{event}'",
        f"\tImage - '{image}'",
        f"\tIni - '{ini}'",
        "\n"
        f"Output Folder - {output}",
        sep=os.linesep)
    
    generate(beat, audio, instruments, event, image, ini, input, output)
    
def generate(beat, audio, instruments, event, image, ini, input, output):

    # Generate output folder
    if (os.path.exists(output)):
        assert os.path.isdir(output)
    else:
        os.makedirs(output)
    
    print("\nMIDI\t" + "="*DIV_NUM_LINES)
    # Generate BEAT.mid if not present
    beat_midi_path = beat
    if not beat.lower().endswith(".mid"):
        audio_in = beat
        if not beat.lower().endswith(".wav"):
            audio_out = os.path.join(input, "BEAT.wav")
            convert_audio(audio_in, audio_out)
            audio_in = audio_out
            
        beat_midi_path = os.path.join(input, "BEAT.mid")
        
        print("Generating 'BEAT.mid'")
        click_to_midi.main(audio_in, beat_midi_path, verbose=VERBOSE)
    
    # Generate notes.mid
    midi_output = os.path.join(output, "notes.mid")
    if os.path.isfile(midi_output):
        already_exists(midi_output)
    else:
        midi_file_paths = [beat_midi_path]
        if event:
            midi_file_paths += [event]
        for instrument in instruments:
            midi_file_paths += [instrument]

        charts_to_notes.main(midi_file_paths, midi_output)
    
    
    print("\nAUDIO\t" + "="*DIV_NUM_LINES)
    # Copy or convert song audio
    audio_out = os.path.join(output, "song.ogg")
    if os.path.isfile(audio_out):
        already_exists(audio_out)
    elif not audio.lower().endswith(".ogg"):
        convert_audio(audio, audio_out)
    else:
        print(f"Copying '{audio}' to '{audio_out}'")
        shutil.copy(audio, audio_out)
    
    if image:
        print("\nIMAGE\t" + "="*DIV_NUM_LINES)
        for base in ["album", "background"]:
            ext = os.path.splitext(image)[1]
            image_out = os.path.join(output, f"{base}{ext}")
            if os.path.isfile(image_out):
                already_exists(image_out)
            else:
                print(f"Generating '{image_out}' from '{image}'")
                if base is "album":
                    create_album(image, image_out)
                else:
                    create_background(image, image_out)
        
    print("\nINI\t" + "="*DIV_NUM_LINES)
    if not ini:
        ini = os.path.join(os.path.dirname(os.path.realpath(__file__)), "template.ini")
    ini_out = os.path.join(output, "song.ini")
    if os.path.isfile(ini_out):
        already_exists(ini_out)
    else:
        print(f"Copying '{ini}' to '{ini_out}'")
        shutil.copy(ini, ini_out)
        
    
def convert_audio(f_in, f_out):
    print(f"Converting '{f_in}' to '{f_out}'")
    audio = AudioSegment.from_file(f_in)
    audio.export(f_out)
    
MAX_RESOLUTION = (2560, 1440)

def create_album(image, image_out):
    image = Image.open(image)
    
    if(image.width > min(MAX_RESOLUTION) or image.height > min(MAX_RESOLUTION)):
        image = image.resize((min(MAX_RESOLUTION), min(MAX_RESOLUTION)))
    image.save(image_out, 'png', quality=80)
    
def create_background(image, image_out):
    image = Image.open(image)
    
    aspect_ratio = image.width / image.height
    aspect_ratio_out_w = 16
    aspect_ratio_out_h = 9
    
    if aspect_ratio > 1:
        width = image.width
        height = int(image.width * (aspect_ratio_out_h/aspect_ratio_out_w))
    else:
        width = int(image.height * (aspect_ratio_out_w/aspect_ratio_out_h))
        height = image.height
    
    resized_image = image.resize((width, width))
    
    left = (resized_image.width - width) / 2
    top = (resized_image.height - height) / 2
    right = left + width
    bottom = top + height
    cropped_image = resized_image.crop((left, top, right, bottom))

    blurred_image = cropped_image.filter(ImageFilter.GaussianBlur(radius=15))

    # Cover placement
    
    # # Place in center full height
    # cover_image = image
    # pos_x = int((width - image.width) / 2)
    # pos_y = 0
    # blurred_image.paste(image, (pos_x, pos_y))
    
    # # Lane comes out of cover
    # cover_image = image.resize((int(image.width*0.6), int(image.height*0.6)))
    # pos_x = int((width - cover_image.width) / 2)
    # pos_y = int((height - cover_image.height) / 2) - int(height*0.1)
    
    # ^^ but smaller
    cover_image = image.resize((int(image.width*0.5), int(image.height*0.5)))
    pos_x = int((width - cover_image.width) / 2)
    pos_y = int((height - cover_image.height) / 2) - int(height*0.2)
    
    # # Place upper right middle    + rep RecursiveGoon for the inspiration
    # cover_image = image.resize((int(image.width*0.5), int(image.height*0.5)))
    # pos_x = width - cover_image.width - int(cover_image.height * 0.2)
    # pos_y = int(cover_image.height * 0.2)
    
    # Border
    border_size = int(width * 0.0015)
    draw = ImageDraw.Draw(blurred_image)
    x1 = pos_x - border_size
    x2 = pos_x + cover_image.width + border_size
    y1 = pos_y - border_size
    y2 = pos_y + cover_image.height + border_size
    
    color = (0, 0, 0)
    draw.rectangle([x1, y1, x2, y2], fill=color)
    
    blurred_image.paste(cover_image, (pos_x, pos_y))
    
    if(blurred_image.width > MAX_RESOLUTION[0]):
        blurred_image = blurred_image.resize(MAX_RESOLUTION)
    blurred_image.save(image_out, 'png', quality=80)

def already_exists(path):
    print(f"'{path}' already exists")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A tool for generating song folders compatable with clone hero')
    parser.add_argument('-i', '--input', required=True, help='An input folder path')
    parser.add_argument('-o', '--output', required=False, default='', help='An output folder path')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')

    args = vars(parser.parse_args())
    if(args['verbose']):
        VERBOSE = True
    
    sys.exit(main(
        args['input'],
        args['output']
    ))
