#!/usr/bin/env python

import os
import sys
from time import time

from mido import MidiFile, MidiTrack, Message, MetaMessage
 
 
def main(in_file, out_file, purge_list):
    
    midi_file = MidiFile(in_file, type=1)
    
    parts = [part for part in midi_file.tracks if "PART " in part.name]
    for part in parts:
        if "star_power" in purge_list:
            purge_note_messages(part, note=116)


    # write file
    with open(out_file, "wb") as f:
        midi_file.save(file=f)

def purge_messages_of_type(track, types):
    indices = []
    for i, message in enumerate(track):
         if message.type in types:
            indices += [i]
            track[i+1].time += message.time

    for i in reversed(indices):
        track.pop(i)

def purge_note_messages(track, note=None, velocity=None):
    assert note or velocity
    
    indices = []
    for i, message in enumerate(track):
        if message.type in ["note_on", "note_off"]:
            if (note == None or message.note == note) and \
               (velocity == None or message.velocity == velocity): 
                indices += [i]
                track[i+1].time += message.time

    for i in reversed(indices):
        track.pop(i)

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='A tool for adjusting aspects of a multitrack midi file for use with Clone Hero')
    parser.add_argument('-i', '--input', required=True, help='A multitrack midi file with all parts')
    parser.add_argument('-o', '--output', default='', help='An output midi file of all parts combined')
    parser.add_argument('--nosp', action='store_true', help='Remove star power gems from all parts of the chart')
    
    args = vars(parser.parse_args())

    in_file =  args['input']
    out_file =  args['output'] if args['output'] != '' else args['input']
    
    purge_list = []
    if(args['nosp']):
        purge_list += ["star_power"]
    
    sys.exit(main(in_file, out_file, purge_list))

