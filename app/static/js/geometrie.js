// Position de chaque broche sur l'appareil, en millimètres, vue de dessus :
// x vers la droite depuis le bord gauche, y vers le bas depuis le bord haut.

export function cleBroche(ri, bi) {
  return `${ri}:${bi}`;
}

export function positionsBroches(fiche) {
  const { largeur, longueur } = fiche.boitier;
  const resultat = [];
  fiche.brochage.rangees.forEach((rangee, ri) => {
    const n = rangee.broches.length;
    const vertical = rangee.cote === "gauche" || rangee.cote === "droite";
    const cote = vertical ? longueur : largeur;
    const debut = rangee.debut ?? (cote - (n - 1) * rangee.pas) / 2;
    rangee.broches.forEach((broche, bi) => {
      const le = debut + bi * rangee.pas;
      let x, y;
      switch (rangee.cote) {
        case "gauche": x = rangee.retrait; y = le; break;
        case "droite": x = largeur - rangee.retrait; y = le; break;
        case "haut": x = le; y = rangee.retrait; break;
        default: x = le; y = longueur - rangee.retrait;
      }
      resultat.push({ cle: cleBroche(ri, bi), rangee, broche, cote: rangee.cote, x, y });
    });
  });
  return resultat;
}

export function libelleBroche(p) {
  const nRangees = p.rangee && p.rangee.nom;
  return `${p.broche.nom} · broche ${nRangees ? `${p.rangee.nom}-` : ""}${p.broche.n}`;
}
