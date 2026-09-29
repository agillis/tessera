# The bedside clock

A screen beside a bed is a clock first. The bedside clock is a tile that takes a whole page: the time as large as
the page allows, with up to three round keys under it for what you reach for at night, such as the bedside lamp, the
bedroom temperature and the front door lock. It needs app 0.4.12 and firmware 0.8.0.

## Using it

1. In ESP Screens, open the screen and add **Bedside clock** from the library. It always fills its page.
2. Drag an entity onto one of the round places under the time, or tap a place and pick an entity in the library.
   A tile that is already on the screen can be dragged onto a place too, and a key can be dragged back onto an empty
   cell.
3. Tap a key to set it up. It is a tile like any other: its name, its icon, what a tap does and, for a lock, whether
   it may unlock. What its clock decides for it (its size, its page and the colour of a card) is not there.

On the screen a key behaves exactly like its tile would: a tap switches the lamp or opens its card as you chose,
holding it opens its card, a lock asks for a second tap before it unlocks, and an alarm panel's circle beats while
it counts down. The key's circle takes the colour of the entity's state, and a temperature shows its value instead
of an icon.

The clock starts without a card behind it, so the digits stand on the page. Choose a background for it like for any
tile if you want the card. For the night, turn on **Dark mode** and the screen's **night hours**, so the page is black
and the backlight dims when you go to bed.

The keys have their names under them on every screen with the standard look. The CYD and the other small screens
with the compact look show the keys alone, since their smallest letters are too small to read in the dark.

## How it is built

A key is a tile without a cell of its own. Everything that knows tiles knows keys; only what places tiles on the grid
leaves them out.

- **The page document** keeps a key as a child of its clock: `children` on the clock's tile, each with the fields of
  a tile but a placement (`page_layout._keys`). The clock owns the order and the keys go with it.
- **The compiled tiles** (`page_layout.compile_tiles`) list a key after the placed tiles, as
  `{"entity": ..., "name": ..., "in": "screen.nightstand", "key": 0, "options": {...}}`. `in` names the tile it
  stands under by its entity; `key` is its place, from 0. Any other entity may be on a screen several times
  (firmware 0.16.0+), a key and a tile of the same entity too, but the bedside clock is on a screen once, so `in`
  always names one tile. Every other part of the add-on
  (the watched entities, history, the layout sensor, the tile limit, the checks when saving) reads this list and
  treats a key as a tile. `core.KEY_HOLDERS` says which tiles hold keys and how many; `core.KEY_DOMAINS` which
  entities may be one (anything but a picture).
- **On the wire** a key's first message names its clock by index (`in`) and its place (`k`) instead of a `slot`. The
  screen says it takes them with the hello flag `tile_keys`; a layout with keys is refused before anything is sent to
  a screen without it, and the add-on asks for firmware 0.8.0 first.
- **On the screen** a key is a `Tile` with `parent` and `key` (`runtime_model.h`). `place()` gives it its clock's page
  and no cell. `place_page` lends it the card of a cell the full-page clock covers, takes that card out of the grid
  (`key_shape`) and puts it where `bedside_layout` says. The card is drawn round (`render_slot`, `w.key`), so its
  colours, icon, busy sheet, tap, hold and animations are the tile's own code. The clock draws the digits and the
  key names (`render_bedside`).
- **The editor** lists a key as a tile with `in` and `key` and a slot of -1 (`model/pages.ts`). The grid shows only
  placed tiles; the clock's card draws its places with the same `TileCard` in its round form, and a click opens the
  normal tile inspector.

### The size of the digits

The digits are one font per board, `bedside_digits`, sized by `FONT_BEDSIDE_SIZE`. `packages/looks/shared/bedside.yaml`
works it out from the glass (`PANEL_W`, `PANEL_H`), the density and the look's own sizes: the largest the whole-page
card takes lying down and standing up, with the keys in a row under the time, in a column beside it, or under the
hours stacked over the minutes. It follows the rules `bedside_layout` lays the clock out with, so a new board gets its
size without a number of its own. A board may still state `FONT_BEDSIDE_SIZE` when a measurement on the glass says so.

`tools/render/run.py` renders the clock with three keys on every board, lying down and standing up, and the screen's
self test fails a board where the digits fit no arrangement or a key leaves its clock. Run it for one board with
`--only bedside`.

### Another tile with keys

A new tile that holds keys needs its entry in `core.KEY_HOLDERS`, a firmware that draws it and lends its keys cards
(`place_page`), and its layout rule. The document, the compiled tiles, the wire, the add-on and the editor's inspector
already work for any holder.
