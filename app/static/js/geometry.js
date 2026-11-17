// Position of each pin on the device, in millimetres, seen from above:
// x grows to the right from the left edge, y grows downwards from the top edge.

export function pinKey(rowIndex, pinIndex) {
  return `${rowIndex}:${pinIndex}`;
}

export function pinPositions(sheet) {
  const { width, length } = sheet.package;
  const positions = [];
  sheet.pinout.rows.forEach((row, rowIndex) => {
    const count = row.pins.length;
    const vertical = row.side === "left" || row.side === "right";
    const sideLength = vertical ? length : width;
    const start = row.start ?? (sideLength - (count - 1) * row.pitch) / 2;
    row.pins.forEach((pin, pinIndex) => {
      const along = start + pinIndex * row.pitch;
      let x, y;
      switch (row.side) {
        case "left": x = row.inset; y = along; break;
        case "right": x = width - row.inset; y = along; break;
        case "top": x = along; y = row.inset; break;
        default: x = along; y = length - row.inset;
      }
      positions.push({ key: pinKey(rowIndex, pinIndex), row, pin, side: row.side, x, y });
    });
  });
  return positions;
}
