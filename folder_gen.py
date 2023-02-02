import os
import sys
import shutil
import argparse
import ffmpeg

import charts_to_notes
import click_to_midi

AUDIO_FORMATS = [".mp3", ".ogg", ".wav", ".flac", ".aac"]
IMAGE_FORMATS = [".png", ".jpg"]

DIV_NUM_LINES = 80

def main(input, output=''):
    
    in_files = [os.path.join(input, f) for f in os.listdir(input) if  os.path.isfile(os.path.join(input, f))]
    
    beat = ""
    audio = ""
    image = ""
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
        "\n"
        f"Output Folder - {output}",
        sep=os.linesep)
    
    generate(beat, audio, instruments, event, image, input, output)
    
def generate(beat, audio, instruments, event, image, input, output):

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
        click_to_midi.main(audio_in, beat_midi_path)
    
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
        # Copy or convert song audio
        ext = os.path.splitext(image)[1]
        image_out = os.path.join(output, f"album{ext}")
        if os.path.isfile(image_out):
            already_exists(image_out)
        else:
            print(f"Copying '{image}' to '{image_out}'")
            shutil.copy(image, image_out)
    
    print("\nINI\t" + "="*DIV_NUM_LINES)
    ini = os.path.join(os.path.dirname(os.path.realpath(__file__)), "template.ini")
    ini_out = os.path.join(output, "song.ini")
    if os.path.isfile(ini_out):
        already_exists(ini_out)
    else:
        print(f"Copying '{ini}' to '{ini_out}'")
        shutil.copy(ini, ini_out)
        
    
def convert_audio(f_in, f_out):
    print(f"Converting '{f_in}' to '{f_out}'")
    (ffmpeg
        .input(f_in)
        .output(f_out, loglevel="quiet")
        .run())

def already_exists(path):
    print(f"'{path}' already exists")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='A tool for generating song folders compatable with clone hero')
    parser.add_argument('-i', '--input', required=True, help='An input folder path')
    parser.add_argument('-o', '--output', required=False, default='', help='An output folder path')

    args = vars(parser.parse_args())
    
    sys.exit(main(
        args['input'],
        args['output']
    ))
