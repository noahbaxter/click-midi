#!/usr/bin/env python

import os
import sys
from time import time

from mido import MidiFile, MidiTrack, Message, MetaMessage
 
PART_TYPES = ["BEAT", "DRUMS", "EVENTS"]
TICKS_PER_BEAT = 480    # clone hero expects this
TOM_NOTES = [110, 111, 112]
SECTION_NOTE = 0

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='A tool for combining multiple parts into a multitrack midi file compatible with Clone Hero')
    parser.add_argument('-i', '--inputs', action='append', nargs='+', required=True, help='A midi file with a single part')
    parser.add_argument('-o', '--output', default='notes.mid', help='An output midi file of all parts combined')
    
    args = vars(parser.parse_args())

    in_files =  [in_file for file_group in args['inputs'] for in_file in file_group]    # flatten to 1D array whether "-i $1 -i $2" or "-i $1 $2"
    out_file = args['output']
    
    # Load up all midi files
    part_dict = {}
    for in_file in in_files:
        # print(MidiFile(in_file, type=1))
        basename = os.path.splitext(os.path.basename(in_file))[0]
        for part in PART_TYPES:
            if part in basename:
                part_dict[part] = MidiFile(in_file, type=1)
                
                break
    
    out_midi = init_midi()
    create_events = True
    
    # append each track
    for part, midi_file in part_dict.items():
        
        adjust_message_timings(midi_file, TICKS_PER_BEAT)
            
        track = midi_file.tracks[0]
        
        if part == "BEAT":
            out_midi.tracks.insert(0, midi_file.tracks[0])
            track = midi_file.tracks[1]
        elif part == "DRUMS":
            purge_messages_of_type(track, ['time_signature'])
            add_toms(track)
        elif part == "EVENTS":
            track = create_sections_from_notes(track)
            create_events = False
            
        track[0].name = part

        out_midi.tracks.append(track)
        
    if create_events:
        track = MidiTrack([
            MetaMessage('track_name', name='EVENTS', time=0),
            MetaMessage('end_of_track', time=0),
        ])
        out_midi.tracks.append(track)        
        
    print_midi(out_midi)
    
    
    # write file
    with open(out_file, "wb") as f:
        out_midi.save(file=f)

def purge_messages_of_type(track, types):
    indices = []
    for i, message in enumerate(track):
         if message.type in types:
            indices += [i]

    for i in reversed(indices):
        track.pop(i)

def adjust_message_timings(midi_file, new_ticks_per_beat):
    multiplier = new_ticks_per_beat / midi_file.ticks_per_beat
    
    for track in midi_file.tracks:
        for message in track:
            message.time = int(message.time * multiplier)

def add_toms(track):
    types = ["note_on", "note_off"]

    indices = []
    for i, message in enumerate(track):
         if message.type in types and message.note in TOM_NOTES:
            indices += [(i, message)]
            
    for (i, msg) in reversed(indices):
        track.insert(i+1, (Message(msg.type, note=msg.note-12, velocity=msg.velocity, time=0)))

def create_sections_from_notes(track):
    out_track = MidiTrack()
    out_track.append(MetaMessage('track_name', name='EVENTS', time=0))
    
    _time = 0
    section_number = 1
    for i, message in enumerate(track):
        if message.type == "note_on":
            sect_time = message.time + _time
            _time = 0
            out_track.append(
                MetaMessage('text', text=f'[section Part {section_number}]', time=sect_time)
            )
            
            section_number += 1
            
        elif message.type == "note_off":
            _time = message.time
            
    out_track.append(MetaMessage('end_of_track', time=0))
    return out_track
    
def print_midi(midi_file):
    print(f"\ntype={midi_file.type}, tracks={len(midi_file.tracks)}, ticks_per_beat={midi_file.ticks_per_beat}")
    for i, track in enumerate(midi_file.tracks):
        messages = []
        name = ""
        for j, message in enumerate(track): 
            if message.type not in messages:
                messages += [message.type]
        print(f"'{track.name}' {i}:", messages)

# INITS
    
def init_midi():
    midi_file = MidiFile()
    # midiutil.MIDIFile()
    
    # midi_file = MIDIFile(1, file_format=1)
    # midi_file.addTrackName(track=0, time=0, trackName="BEAT")

    return midi_file

def load_part(midi_file, part_path):
    
    return

# Passthrough to main

if __name__ == '__main__':
    # sys.exit(main())
    sys.exit(main())

