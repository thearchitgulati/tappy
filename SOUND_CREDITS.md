# Sound credits

Every recording used by every pack is sourced from freesound.org.
Licenses noted per-source; CC0 = no attribution required, commercial use
explicitly permitted. CC-BY requires attribution (included below).

## Gaming Click

- Regular clicks: **Keyboard_Click.wav** by Feedbackdesignz (CC0) +
  **mechanical keyboard click** by getwecked, Razer BlackWidow 2 (CC0)
  https://freesound.org/people/Feedbackdesignz/sounds/245716/
  https://freesound.org/people/getwecked/sounds/764661/
- Space: **Keychron k10 space_bar** by Sadiquecat (CC0)
  https://freesound.org/people/Sadiquecat/sounds/789630/
- Enter: **Enter Key Press Mechanical Keyboard** by alpinemesh, Corsair K70 RGB (CC0)
  https://freesound.org/people/alpinemesh/sounds/627647/
- Delete: shared FUJITSU sample, see below

## Logitech Typing

- Regular clicks + Space + Enter: all sliced from **keyboard.mp3** by
  kfrance100, Logitech G710+ continuous typing recording (CC0) -- Space/
  Enter are the two loudest non-outlier onsets in that same recording, a
  best-effort pick of the physically larger keys, not verified per-key
  ground truth, but guaranteed to be the same real keyboard.
  https://freesound.org/people/kfrance100/sounds/381229/
- Delete: shared FUJITSU sample, see below

## Computer Keyboard

- Regular clicks: yottasounds "Computer Keyboard - single key - type 1/2/3/4.wav" (CC0)
- Space: yottasounds "Computer Keyboard - single key - type 6/7 - space bar.wav" (CC0)
  https://freesound.org/people/yottasounds/
- Enter + Delete: **Sadiquecat's FUJITSU keyboard** recordings (CC0) --
  same physical keyboard for both
  https://freesound.org/people/Sadiquecat/sounds/799116/ (Enter)
  https://freesound.org/people/Sadiquecat/sounds/799115/ (Delete)

## Typewriter

- Regular clicks: yottasounds "Typewriter - single key - type 1/2/3.wav" +
  "Typewriter - Very Old Typing Sounds.wav" (CC0)
  https://freesound.org/people/yottasounds/
- Space: **typewriter_manual_spacebar.wav** by magedu (CC-BY 4.0 -- attribution required)
  https://freesound.org/people/magedu/sounds/277299/
- Enter: **Typewriter Carriage Return.wav** by ramsamba (CC0) -- used at
  its full original length rather than windowed to ~90ms, since a carriage
  return is a longer mechanical action than a single key click
  https://freesound.org/people/ramsamba/sounds/318686/
- Delete: none -- most manual typewriters had no backspace key, so this
  falls back to the regular click sound rather than using a mismatched
  modern sample

## Apple MacBook

- Regular clicks + Space + Enter + Delete: all sliced from **Computer
  keyboard typing and keystrokes - Apple MacBook Pro 2018** by khenshom
  (CC0) -- Space/Enter are the two loudest non-outlier onsets in that same
  recording (see Logitech Typing note above re: heuristic picking); Delete
  is another onset from the same recording, picked from the same
  percentile band as the regular clicks after the shared FUJITSU Delete
  sample clashed badly with this pack's softer scissor-switch character.
  https://freesound.org/people/khenshom/sounds/565645/

## Cherry MX Blue

- Regular clicks + Space + Enter: all sliced from **Typing (Cherry MX Blue
  Switches)** by jameslovescode (CC0) -- Space/Enter picked the same way
  as Logitech Typing/Apple MacBook above.
  https://freesound.org/s/400699/
- Delete: shared FUJITSU sample, see below

## Shared Delete sample

- **FUJITSU Computers Keyboard - Delete key Press Mono** by Sadiquecat (CC0)
  https://freesound.org/people/Sadiquecat/sounds/799115/
  Used by Gaming Click, Logitech Typing, Apple MacBook, and Cherry MX Blue
  (a generic office-keyboard Delete, reused since Delete/Backspace is a
  regular-sized key without the size-driven acoustic distinctiveness that
  justified sourcing Space/Enter per-pack).

## Notes

- Confirm (copy/paste) chimes are synthesized in every pack, not sourced
  from any recording.
- All click/space/enter/delete samples are peak-normalized (see
  Scripts/pick_and_normalize.py) -- raw sliced onsets varied up to ~14x in
  loudness within a pack before this, which read as "too loud"/"skipping."
- Attribution required for magedu's typewriter spacebar sample if shipped
  publicly -- surface this in an in-app credits/about screen.
