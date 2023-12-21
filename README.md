# Click to Midi
This is a quick and dirty python tool that allows you export tempo and time sig information from DAWs that won't export midi 0 files (i.e. Ableton)!!

## Instalation
#### MacOS
1. Install brew by opening a Terminal and running `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
2. Install latest python with `brew install python3`
3. Navigate to repo by right clicking the folder -> *Services* -> *New Terminal at Folder*
4. Install dependencies by running `pip3 install -r requirements.txt`
   
### How to Use
#### Click to Midi
1. Create an audio click track from the samples provided in the **clicks** folder (or your own with arguments). There's a couple of rules for making these.
   1. All bars MUST start with the barline *bar.wav*.
   2. After the bar has begun, pick ONLY 1 subdivision (i.e. 8th, 16th) and add as many notes as you want the measure long. 
      1. DO NOT mix and match subdivisions.
      2. You MUST have at least 2 beats in a measure. you cannot have 2 barlines s in a row.
      3. You MUST use the same subdivision as your DAW or the midi tempo will be scaled too fast or too slow
   3. Render the click audio at the SAME sample rate as the click samples, i.e. 44100 for the provided samples.
2. Run `python3 click_to_midi.py -i click_audio.wav` and your result will be output to `notes.mid`. If you import this midi file it'll contain the generated tempo/time sig information.
   
Enjoy!

(ps better documentation coming)

#### Charting Tools
documentation to come...