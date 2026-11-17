// Pins with their position on the device, in millimetres, seen from above:
// x grows to the right from the left edge, y grows downwards from the top edge.
// Positions are computed by the server (app/sheets.py), which also builds the 3D model from them.

export function pinKey(rowIndex, pinIndex) {
  return `${rowIndex}:${pinIndex}`;
}

export function pinPositions(sheet) {
  return sheet.pinout.rows.flatMap((row, rowIndex) => row.pins.map((pin, pinIndex) => ({
    key: pinKey(rowIndex, pinIndex), row, pin, side: row.side, x: pin.x, y: pin.y,
  })));
}
