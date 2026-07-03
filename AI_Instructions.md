# SD Card Transfer Tool - Design & Implementation Specification

## Project Overview

### Purpose

This application is being built to simplify the daily transfer of photos and videos from multiple SD cards during extended road trips and expeditions.

The primary use case is multi-week vehicle expeditions such as:

* Trans-Taiga Road (Quebec)
* Trans-Labrador Highway
* Dempster Highway / Tuktoyaktuk
* Other remote North American camping and overlanding trips

The user expects to generate hundreds of gigabytes of media each day from multiple recording devices.

Typical devices include:

* DJI Drone
* GoPro Action Camera
* Vehicle Dashcam
* Samsung Phone
* Future cameras and recording devices

Most of the data consists of large video files:

* MP4
* MOV
* JPG
* JPEG
* DNG
* PNG
* WAV
* SRT
* THM
* LRV
* Other common media formats

This application is the first component of a larger expedition media management workflow.

---

# Operational Environment

The application is designed around the real-world conditions in which it will be used.

At the end of a travel day the user will typically:

* Have driven 8–12 hours.
* Be physically and mentally tired.
* Be camping in a remote location or staying in a hotel.
* Have limited time before going to sleep.
* Be using a Windows 11 laptop.
* Have one or more SD cards to archive.
* Have a Western Digital 6 TB portable hard drive connected.

This process will be repeated nearly every evening during a two to three week expedition.

Because the user is often fatigued, the application should minimize opportunities for mistakes.

The application should always prioritize **data safety over speed**.

---

# Why This Application Exists

The media being transferred is often impossible or prohibitively expensive to recreate.

Examples include:

* Drone footage over remote wilderness
* Wildlife encounters
* Northern lights
* Timelapse photography
* Ocean crossings
* Remote roads
* Family memories
* Campsites
* Scenic overlooks
* One-time travel experiences

If files are accidentally overwritten, deleted, or copied incorrectly, they may be lost forever.

For that reason this application is intentionally conservative.

It should behave more like an aviation checklist than a traditional file copy program.

The goal is not to build the fastest copy utility.

The goal is to build the safest one.

---

# Design Philosophy

Every design decision should support the following principles.

## Safety First

Never overwrite existing files.

Never automatically delete files from the SD card.

Never assume drive letters.

Always verify copied files.

Always produce logs.

Always make it obvious where files are being copied.

---

## Minimize User Decisions

The application should ask only the information it truly needs.

The user should never need to remember:

* Drive letters
* Folder structures
* Destination paths
* Archive organization

The application should determine these automatically whenever possible.

---

## Fool Proof

Assume the user is tired.

Assume the user may not notice mistakes.

The application should actively prevent accidental data loss.

---

## Simple

The application should remain intentionally simple.

Reliability is more important than cleverness.

Readable code is preferred over highly optimized code.

---

# Long-Term Vision

Although the initial version will be a console application, the architecture should support future enhancements such as:

* Windows desktop GUI
* SHA-256 verification
* Automatic duplicate detection
* Multi-drive backup
* Automatic thumbnail generation
* GPS track organization
* Expedition journal generation
* Integration with DJI and GoPro folder structures
* Media cataloging
* Search capability
* Future cloud synchronization

The first version should focus solely on safe and reliable file transfer.

---

# Target Platform

Operating System

* Windows 11 only

Development Language

* Python 3.12+

Development Environment

* Visual Studio Code
* GitHub Copilot or Claude Code
* PowerShell terminal

This application is **not** intended to run under Linux or WSL.

It should use Windows-native APIs where appropriate.

---

# Overall Workflow

The ideal workflow should look like this.

1. Insert SD card.
2. Connect Western Digital portable drive.
3. Launch the application.
4. Answer a few simple questions.
5. Confirm the transfer.
6. Wait for verification.
7. Receive a clear indication whether the SD card is safe to format later.

The entire interaction should require less than one minute of user attention.

---

# Functional Requirements

## Detect the Portable Hard Drive

The application should automatically locate the archive drive.

It should detect the drive using its Windows **Volume Label**, **not** the drive letter.

Example labels:

```
WD_BLACK_6TB
WD_BLACK
EXPEDITION
```

Drive letters should never be hardcoded because Windows may assign different letters.

If multiple archive drives are found, the application should ask the user which one to use.

If no archive drive is found, the application should stop with a clear error message.

---

## Detect Available SD Cards

The application should detect removable drives and display them.

Example:

```
Detected Removable Drives

E:\  DJI_SD
G:\  GOPRO
H:\  Untitled
```

The user simply selects the desired source drive.

---

# Questions to Ask

The application should ask only the following.

## 1. Date

Prompt:

```
Enter date (press Enter for today):
```

Default:

```
YYYY-MM-DD
```

Example:

```
2027-05-12
```

---

## 2. Theme

Prompt:

```
Enter today's theme:
```

Examples:

```
Taiga Out
Clearwater to Hohenwald
Drone Campsite
Churchill Falls
Northern Lights
```

The application should normalize the folder name.

Example:

```
Taiga Out

becomes

taiga-out
```

---

## 3. Device

Present a menu.

```
1 DJI

2 GoPro

3 Dashcam

4 Phone

5 Other
```

---

## 4. SD Card

Present the detected removable drives.

Example:

```
1 E:\ DJI_SD

2 G:\ GOPRO
```

---

# Destination Folder Structure

The archive should always use the following layout.

```
Expedition_Archive
│
├── 2027-05-12
│   └── taiga-out
│       ├── DJI
│       ├── GoPro
│       ├── Dashcam
│       └── Phone
│
└── _logs
```

Destination example:

```
F:\Expedition_Archive\2027-05-12\taiga-out\DJI\
```

Folders should be created automatically.

---

# File Types

Only copy supported media files.

Examples:

```
.mp4
.mov
.jpg
.jpeg
.png
.dng
.wav
.srt
.thm
.lrv
.insv
```

The list should be configurable.

---

# Copy Rules

## Never Overwrite

If destination does not exist:

```
Copy
```

If destination exists and file sizes match:

```
Skip
Log as Duplicate
```

If destination exists but file sizes differ:

```
Create

filename__copy2.ext
```

If necessary:

```
filename__copy3.ext
filename__copy4.ext
```

No existing file should ever be modified.

---

# Verification

After every copy:

Compare

```
Source Size

Destination Size
```

If equal:

```
Verified
```

Otherwise:

```
Verification Failed
```

The application should be designed so SHA-256 verification can be added later.

---

# Confirmation Screen

Before copying, display a clear summary.

Example:

```
Archive Drive

F:\ WD_BLACK_6TB

Source

E:\ DJI_SD

Destination

F:\Expedition_Archive\
2027-05-12\
taiga-out\
DJI

Files Found

184

Total Size

73.4 GB

Proceed?

Type YES
```

---

# Final Status

Successful transfer:

```
COPY COMPLETE

Files Copied

184

Duplicates

0

Conflicts Renamed

0

Errors

0

Verified

184 / 184

SAFE TO FORMAT SD CARD
```

If any error occurs:

```
COPY COMPLETED WITH ERRORS

Files Copied

181

Errors

3

Verified

181 / 184

DO NOT FORMAT SD CARD

Review the transfer log.
```

The success or failure message should be visually obvious.

---

# Logging

Every run should generate:

```
transfer_YYYY-MM-DD_HHMM.log

manifest_YYYY-MM-DD_HHMM.csv
```

Store logs in:

```
Expedition_Archive\_logs\
```

Manifest columns:

```
Timestamp

Source Path

Destination Path

File Size

Status

Verification Status

Notes
```

---

# Configuration

Use a JSON configuration file for:

* Archive root folder
* Portable drive volume labels
* Device list
* Supported file extensions
* Verification mode
* Future options

Avoid hardcoding values whenever practical.

---

# Safety Requirements

The application must **never**:

* Delete files from the SD card.
* Format an SD card.
* Overwrite destination files.
* Assume a fixed drive letter.
* Copy files to the laptop's internal drive by mistake.
* Continue after a failed verification without clearly warning the user.

Every operation should fail safely.

---

# Code Quality Requirements

The code should be:

* Modular
* Well documented
* Strongly typed where practical
* Readable
* Easy to maintain
* Easy to extend

Prefer explicit code over clever code.

Avoid unnecessary complexity.

---

# Suggested Project Structure

```
sd-transfer-tool/

│
├── transfer_sd.py
├── config.json
├── requirements.txt
├── README.md
├── transfer/
│   ├── drive_detection.py
│   ├── copier.py
│   ├── verifier.py
│   ├── logger.py
│   ├── manifest.py
│   ├── config.py
│   └── utils.py
│
└── tests/
```

Separate responsibilities into logical modules rather than one large script.

---

# Development Phases

## Phase 1

Console application.

Features:

* Detect archive drive.
* Detect SD cards.
* Ask user questions.
* Create destination folders.
* Copy files.
* Verify by file size.
* Produce logs.
* Produce manifest.

---

## Phase 2

Improve robustness.

Features:

* Better error handling.
* Dry-run mode.
* Configuration improvements.
* Better progress display.
* More detailed reporting.

---

## Phase 3

Windows application.

Features:

* Package with PyInstaller.
* Desktop shortcut.
* Simple GUI.
* Drag-and-drop support.
* Improved progress indicators.

---

# Final Goal

The application should feel less like a generic file copy utility and more like a trusted expedition assistant.

At the end of every travel day, the user should be able to launch the application, answer a few simple questions, and confidently archive an entire day's worth of irreplaceable media with almost no opportunity for user error.

The software should emphasize **clarity, safety, and confidence** over speed or feature count. If a design decision ever requires choosing between convenience and protecting the user's data, always choose the option that best preserves the integrity of the archived media.
