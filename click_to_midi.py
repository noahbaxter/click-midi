#!/usr/bin/env python

import sys
import math
import argparse

import numpy as np
import soundfile as sf

from midiutil.MidiFile import MIDIFile

ZERO = 1e-8
BPM_TOL = 0.05  # min change for a new BPM to be used

def main():

    global SAMPLE_RATE, REDUCE_BPM_CHANGES, REDUCE_SIG_CHANGES, PRINT_BPM_CHANGES, PRINT_SIG_CHANGES
    
    
    parser = argparse.ArgumentParser(description='A tool for converting click tracks to midi with tempo and time signature changes preserved')
    parser.add_argument('-i', '--input', required=True, help='An input audio file of your clicktrack in full')
    parser.add_argument('-i1', '--click_bar', required=False, default='clicks/bar.wav', help='An input audio file of your barline click sound')
    parser.add_argument('-i4', '--click_4th', required=False, default='clicks/quarter.wav', help='An input audio file of your quatre note click sound')
    parser.add_argument('-i8', '--click_8th', required=False, default='clicks/eigth.wav', help='An input audio file of your eigth note click sound')
    parser.add_argument('-i16', '--click_16th', required=False, default='clicks/sixteenth.wav', help='An input audio file of your sixteenth note click sound')
    parser.add_argument('-i32', '--click_32nd', required=False, default='clicks/thirtysecond.wav', help='An input audio file of your thirty second note click sound')
    parser.add_argument('-o', '--output', default='BEAT.mid', help='An output midi file to contain your tempo')
    
    parser.add_argument('-sr', '--sample_rate', required=False, default=44100, help='The sample rate of all audio files')
    parser.add_argument('-a', '--add_instrument', required=False, help='Allows the packaging of this metronome with other midi instruments in a single multitrack')
    
    parser.add_argument('-m', '--maximize', action='store_true', help='Forces a BPM or time signature change midi event on every click, even when unecessary')
    parser.add_argument('-v', '--verbose', action='store_true', help='Display all BPM and time changes')
    
    args = vars(parser.parse_args())

    in_file = args['input']
    out_file = args['output']
    SAMPLE_RATE = args['sample_rate']
    
    REDUCE_BPM_CHANGES = not args['maximize']
    REDUCE_SIG_CHANGES = not args['maximize']
    
    PRINT_BPM_CHANGES = args['verbose']
    PRINT_SIG_CHANGES = args['verbose']

    # create click_array
    click_dicts = [
        {"division": 1, "path": args['click_bar']},
        {"division": 4, "path": args['click_4th']},
        {"division": 8, "path": args['click_8th']},
        {"division": 16, "path": args['click_16th']},
        {"division": 32, "path": args['click_32nd']},
    ]
    init_click_dicts(click_dicts=click_dicts)
    
    clock_audio = prepare_audio(in_file)
    click_arr = create_click_arr(audio=clock_audio, click_dicts=click_dicts)
    midi = create_midi(click_arr=click_arr)

    with open(out_file, "wb") as f:
        midi.writeFile(f)

def create_click_arr(audio, click_dicts):

    silent = True
    click_start = 0

    click_arr = []
    
    for index, sample in enumerate(audio):

        # Detect click begin
        if abs(sample) > ZERO and silent:
            click_start = index
            silent = False

        # Detect click end
        elif all(abs(s) < ZERO for s in audio[index:index+10]) and not silent:
            silent = True
            click_arr += [{
                "start_samples": click_start,
                "division": find_click_division(input_audio=audio[click_start:index], 
                                                click_dicts=click_dicts)
            }]

    return click_arr

def create_midi(click_arr): 
    midi_file = init_midi()
    
    bar_complete = False
    bar_start = 0
    time_slip = 0
    
    bpm = None
    
    numerator = 1
    denominator = None
    time_sig = None

    for index in range(len(click_arr)):
        division = click_arr[index]["division"]
        
        # fixes missing last notes
        if index == len(click_arr) - 1 and division != 1:
            numerator += 1
            division = 1
        
        # time signatures
        if division == 1:
            if index:
                if numerator == 1:
                    raise Exception("all bars must have more than 1 beat")
                
                if not REDUCE_SIG_CHANGES or time_sig != (numerator, denominator):
                    time_sig = (numerator, denominator)
                    
                    if PRINT_SIG_CHANGES:
                        print(f"SIG: {time_sig}")
                    midi_file.addTimeSignature(track=0,
                                               time=bar_start - time_slip,
                                               numerator=numerator,
                                               denominator=int(math.log(denominator, 2)),
                                               clocks_per_tick=24)

                bar_complete = True
            
        else:
            if not denominator:
                denominator = division
            elif denominator != division:
                raise Exception("cannot have different division clicks in the same measure")
            
            numerator += 1

        # once sig is determined, calc and apply bpm
        if bar_complete:
            
            # fixes missing last note
            if index == len(click_arr) - 1:
                index += 1
                
            for jndex in range(bar_start, index):
                
                # add click notes
                midi_file.addNote(track=0, 
                                  channel=0,
                                  pitch=12 if jndex == bar_start else 13,
                                  time=jndex - time_slip, 
                                  duration=4/denominator,
                                  volume=127)
                
                # add bpm
                try:
                    time_between_samples = click_arr[jndex+1]["start_samples"] - click_arr[jndex]["start_samples"]
                    new_bpm = round((4/denominator) * 60 * SAMPLE_RATE / time_between_samples, 2)
                    
                    # Only change BPM if different enough
                    if not REDUCE_BPM_CHANGES or (not bpm or abs(new_bpm - bpm) > BPM_TOL):
                        bpm = new_bpm
                        
                        if PRINT_BPM_CHANGES:
                            print(f"BPM: {bpm}")
                        midi_file.addTempo(track=0, 
                                           time=jndex - time_slip, 
                                           tempo=bpm)

                except IndexError:
                    # If last note, no new bpm needed 
                    pass 
                
                # handle 8th/16th/32nd note placements
                if math.log(denominator, 2).is_integer() and denominator > 4:
                    time_slip += 1 - (4/denominator)
            
            # prepare for next bar
            numerator = 1
            denominator = None
            bar_start = index
            bar_complete = False

    return midi_file

# INITS

def init_click_dicts(click_dicts):
    for d in click_dicts:
        d["audio"] = prepare_audio(d["path"])
        
        
    # ensure no 2 sounds will get mixed up
    # likely any two sounds at the same length and pitch will probably fail here
    low = 0
    while low < len(click_dicts):
        for i in range(low+1, len(click_dicts)):
            if get_zcr(click_dicts[low]["audio"]) == get_zcr(click_dicts[i]["audio"]):
                print(f"Two clicks samples, {click_dicts[low]['division']}:{click_dicts[low]['path']} and {click_dicts[i]['division']}:{click_dicts[i]['path']}, sound too similar")
                exit()
        low += 1
    
def init_midi():
    midi_file = MIDIFile(1, file_format=1)
    midi_file.addTrackName(track=0, time=0, trackName="BEAT")

    return midi_file

# DSP UTILS
def find_click_division(input_audio, click_dicts):
    for division, click_audio in ((d["division"], d["audio"]) for d in click_dicts):

        # the lazy way
        if get_zcr(click_audio) == get_zcr(input_audio):
            return division
        
    # backup in case lazy way doesn't work
    best_division = ""
    lowest_error = None
    for division, click_audio in ((d["division"], d["audio"]) for d in click_dicts):
        error = get_sample_identicality(input_audio, click_audio)
        
        if not best_division or not lowest_error or error < lowest_error:
            best_division = division
            lowest_error = error
            
    return best_division
        
# MATH UTILS

# zero crossing rate - thanks stooart for the suggestion :)
def get_zcr(audio_buffer):
    assert audio_buffer.ndim == 1

    polarity = ""
    crossing_count = 0

    for s in audio_buffer:
        if s > 0 and polarity != "positive":
            polarity = "positive"
            crossing_count += 1

        elif s < 0 and polarity != "negative":
            polarity = "negative"
            crossing_count += 1

    return crossing_count

# sample identicality - just how "exactly the same" are these two sounds sample by sample?
def get_sample_identicality(audio_1, audio_2):
    assert audio_1.ndim == audio_2.ndim == 1

    audio_1 = np.trim_zeros(audio_1/np.linalg.norm(audio_1))
    audio_2 = np.trim_zeros(audio_2/np.linalg.norm(audio_2))
    min_len_samples = min(len(audio_1), len(audio_2))

    cum_error = 0
    for index in range(min_len_samples - 1):
        cum_error += abs(audio_1[index] - audio_2[index])
    
    return cum_error    # lel

def prepare_audio(path):
    audio, sr = sf.read(path)
    
    if sr != SAMPLE_RATE:
        raise Exception(f"Incorrect sample rate: {path} is {sr}hz, expected {SAMPLE_RATE}hz")
    
    if audio.ndim != 1:
        audio = np.mean(audio, axis=1)
    
    audio = audio/np.linalg.norm(audio)
    
    return audio

# Passthrough to main

if __name__ == '__main__':
    sys.exit(main())
