A library for calculating optimal routes by railroad for each train for the 18xx family of board games.

This is intended to support most 18xx games. The common route finding rules and value calculations are hard-coded, and game specific rules are configured by a set of JSON files (distributed in the package), which setup things like the board layout and available trains. More complex game-specific rules are implemented via game-specific modules and hooks. There are almost certainly features I haven't accounted for, as there are many 18xx games, and I haven't played them all. Those features will be added over time, as I support more games.

The input is a set of CSV files, which form a snapshot of the game's current state. Some basic validation is performed, such as tiles not running off the board and stations not overflowing any cities. The output is a route for each of the requested railroad's trains, presented as both every space used, and as the list of stops (and their values) counted.

Currently supported games: 1846, 1889

Usage
=====
``calc-route <GAME> <RAILROAD> <BOARD STATE> <RAILROAD STATES> [-p <PRIVATE COMPANY STATE>]``

Using the configuration files for GAME, find the best set of routes that can be run by RAILROAD, given the BOARD STATE and RAILROAD STATE (and optionally PRIVATE COMPANY STATE).

Positional
##########
``GAME`` is the name of the game whose configuration files should be used (e.g. 1846). This will determine the game board, available tiles and trains and railroads, as well as some game rules (such as phase names and when private companies close).

``RAILROAD`` is the name of the railroad being run. You may use its full name, or one of its nicknames. The railroad must be listed in RAILROAD STATES (described below).

Board State
-----------
``BOARD STATE`` is a filepath to a CSV file which contains tile coordinates and orientations. Validation is performed to confirm no tiles run off the board, or into the side of a built-in red (off-board) or gray space. No check on tile inventory is currently performed.

The format of each row is "coordinate; tile ID; orientation". For example, ``D14; 15; 4``. Note the use of semi-colons as column separators.

``coordinate`` refers to the coordinate system on the board. Attempting to place a tile on an illegal space (e.g. not on the map, over a built-in gray tile, etc) will raise a ValueError. If 2 rows provide the same coordinate, they cannot indicate the same color tile. No check is performed that the older tile preserves the new one's path.

``tile ID`` refers to the ID number printed on the tile.

``orientation`` is a value from 0 to 5 (inclusive). Orientation 0 matches its image on `Keith Thomasson's 18xx Tiles Database <http://www.fwtwr.com/18xx/tiles/index.asp>`_. Some tile sets on the site are displayed with a flat bottom edge. To align them with the other tiles, rotate them 30 degrees COUNTERCLOCKWISE to get orientation 0. Other orientations are determined by rotating 60 degrees CLOCKWISE from orientation 0.


Railroad States
---------------
RAILROAD STATES is the filepath to a CSV containing which railroads are "in play". Railroads in this file have their home station automatically placed, in addition to the other specified stations.

Each row can take 2 formats. The less common (and simpler) one is "name; removed". For example, ``Pennsylania Railroad; removed``. In some games, home stations are treated differently whether a railroad was removed from the game (e.g. due to player counts) or if it just hasn't floated yet. This allows that distinction to be made.

The format of each row is "name; trains; stations". For example, ``Baltimore & Ohio; 4 / 6, 6; C15, D6: E5, G7``. Note the use of semi-colons as column separators.

``name`` is the full name of the railroad. This must match one of the railroads in the railroads.json file, which will be the same as in the game. Any railroad which doesn't show up in this file is assumed to have not yet placed its home station.

``trains`` is a comma-separated list of trains. This must match on of the trains in the trains.json file (whitespace is removed before comparison). There is no limit on the numbed of trains per railroad.

``stations`` is a command-separated list of coordinates. These are checked to ensure they are cities, and that they have not gone over capacity. For each station in a split city (i.e. a city whose slots are not clustered), either its branch or a unqiue exit must be indicated. A branch is made up of the coorindates of each neighbor of the station slot, surrounded by square brackets and separated by spaces. A unique exit is just the coordinate of the unique exit. In the example above, Baltimore & Ohio has a station on D6 (Chicago), on the branch which runs through unqiue exit E5.

Private Company State (-p | --private-companies-file)
-----------------------------------------------------
PRIVATE COMPANY STATE is the filepath to a CSV containing which private companies are in play. The exact interpretation will be determined by the needs of the game, and key off of the name of the private company. Note that each game is only guaranteed to implement private companies which have an impact on train routes.

Each row's format will be "name; owner; coordinate". For example, ``Steamboat Company; Grand Trunk; G19``. Note that each game defines its own parser, so this format might differ between games, although the intention is to adhere to it as much as possible.

``name`` is the name of one of the private companies in the game. If a private company does not show up in this file, it is assumed to be owned by a player.

``owner`` is the name of the railroad which owns the private company.

``coordinate`` is the coordinate that this private company impacts, if relevant. This will mostly be relevant for private companies which place tokens. It can be omitted for private comapnies which don't impact the board (e.g. 1846's Mail Contract).

Game Specific Notes
===================
1846
####
All private company entries follow the standard format.

- Steamboat Company and Meat Packing Company: validate their token is placed on a legal space, if it is placed.
- Big 4 and Michigan Southern: ignores the coordinate argument. If omitted or an owner is not listed, and private companies have not closed, a station owned by no one is placed on their home tile. If it is owned, that station is assigned to the owning railroad.
- Mail Contract: ignores the coordinate argument. Modifies the route value automatically.

1889
####
Does not validate the port tile is placed on a port space. The code cannot currently handle a space which can be upgraded to multiple different types of tiles.

No private companies impact route finding or route values. A couple do impact tile validity, but I don't think it's worth it.
