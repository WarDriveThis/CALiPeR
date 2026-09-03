# CALiPeR
Counter LPR read-and-display system
Real-time Counter License-Plate-Reader collection and display obfuscation

Overview
Collects local, active license plate strings and re-displays on e-paper under 850NM illumination to generate Flock/LPR reads at cameras. Generates data within the LPR back-end system that render the data less usable for searches violating the 4th amendment. Active privacy protection for the surrounding environment (with volume).
More detail in README-MORE.md

Hardware Options
Currently built for Raspberry PI 4 B with compatible connected camera and Waveshare 7.5 inch e-paper display. Other platforms and displays certainly possible. 7.5 chosen for cost and distance read balance.
Optional 850 Nanaometer illumination LED strip and 850 NM transparent cover for stealth without impacting LPR readability.

Quick Start
Documentation contains all information required to build and flash the device. Fully operational as developed. Built as an Open Source proof of concept using Claude. Claude now declines to participate in further development, so users are welcomed to modify and advance the code and deployment platform as they like.
All configuration flags available through included on-board user interface. Adjust camera settings with some caution as they have significant impact on results and are functional as delivered. 

Features
Reads nearby license plate text
Stores acquired or manually entered license plates in a local pool
Randomly displays plate strings from the pool on the e-paper display for the retention period and display duration configured on the user interface. 
Typical use is simply to install and allow the device to collect legitimate, locally active reads, then allow those strings to be read at additional times and locations effectively blurring the data and denying the data user the ability to reliably perform broad or associative searches since many plates will appear in places the legitimate vehicle was not.

License
GPLv3

CALiPeR is distributed under the GNU General Public License version 3.
See the file LICENSE for details.

This file is part of CALiPeR. CALiPeR is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>. 
