# Neue Logik zur Bewertung von Produkten basierend auf Sucheingabe

def bewerte_treffer(produkt, suchbegriff, grundstoff_liste):
    import re

    suchbegriff = suchbegriff.lower()
    produkt_lower = produkt["Produkt"].lower()
    menge = produkt.get("Menge", "").lower()
    einheit = produkt.get("Einheit", "").lower()
    reinheit = produkt.get("Reinheit", "")

    score = 0.0

    # 1. Grundstoff identifizieren und prüfen
    grundstoff_treffer = None
    for eintrag in grundstoff_liste:
        name = eintrag["Name"].lower()
        synonyme = [s.strip().lower() for s in eintrag["Synonyme"].split(";") if s.strip()]
        if name in suchbegriff or any(s in suchbegriff for s in synonyme):
            if name in produkt_lower or any(s in produkt_lower for s in synonyme):
                grundstoff_treffer = name
                score += 0.5
                break

    if not grundstoff_treffer:
        return 0.0  # kein relevanter Grundstoff => irrelevant

    # 2. Reinheit erkennen und bewerten
    reinheits_match = re.search(r"[>≥]?\s?([0-9]+,[0-9]+|[0-9]+)\s?%", suchbegriff)
    if reinheits_match:
        try:
            reinheit_gesucht = float(reinheits_match.group(1).replace(",", "."))
            produkt_reinheit = float(re.sub(r"[^0-9,]", "", reinheit).replace(",", "."))
            if produkt_reinheit >= reinheit_gesucht:
                score += 0.3
        except:
            pass

    # 3. Menge bewerten
    menge_match = re.search(r"\b(\d+(?:[.,]\d+)?)\s?(ml|l)\b", suchbegriff)
    if menge_match:
        gesuchte_menge = float(menge_match.group(1).replace(",", "."))
        gesuchte_einheit = menge_match.group(2)

        try:
            produkt_menge = float(menge.replace(",", "."))
            if produkt_menge == gesuchte_menge and einheit == gesuchte_einheit:
                score += 0.2
        except:
            pass

    return round(score, 2)
