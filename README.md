### Project Erridium
# AI Dubbing

## Details:
Add stuff here

## Screenshots and samples:
| Source | target |
| ------ | ------ |
| [english](https://github.com/dragonblood/Eridium/blob/master/Eridium/backend/graph.mp4) | [spanish](https://github.com/dragonblood/Eridium/blob/master/Eridium/backend/output/dubbedVideos/es.mp4) |
||[russian](https://github.com/dragonblood/Eridium/blob/master/Eridium/backend/output/dubbedVideos/ru.mp4) |

## Setup:
python dubber.py graph.mp4 output "en" --targetLangs "es"

## Todo:
 - [ ] Frontend where user can upload 
 - [x] Upload the video to bucket *(Creating a bucket to store temporary stuff).*
 - [x] Parse audio from video file.
 - [x] Transcribe the audio *(Ask user for expected keywords in speech).*
 - [x] Translate the Transcription to user desired language.
 - [x] Convert text to speech.
 - [ ]  Clone the voice to match with subject(s).
 - [ ] Use neural puppetry to match facial expression *(Optional, Too expensive).*
 - [ ] Slow down or speed up the resulting audio to watch video comfortably with original source *(I dont think i'll do this but if anyone wants welcome).*
 - [x] Merge the audio with video.
