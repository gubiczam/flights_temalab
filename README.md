# ✈️ Okos Utazástervező

> Adatalapú döntéstámogató modul és ajánlórendszer repülőjegy-vásárláshoz, fókuszban a megbízhatósággal.

## 📖 A probléma
Amikor egy átlagember vagy egy üzleti utazó repülőjegyet keres (pl. Skyscanneren), a rendszerek jellemzően csak az árat és az utazási időt mutatják. Egy szoros átszállásnál vagy fontos találkozónál azonban a legkritikusabb faktor a **megbízhatóság**. Hiába tűnik jónak egy esti járat, ha az adatok alapján az esetek 40%-ában legalább fél órát késik. Jelenleg a felhasználók "vakon" választanak a járatok között a késési kockázat ismerete nélkül.

## 💡 A megoldás
A projekt célja egy utasközpontú, adatalapú döntéstámogató modul elkészítése. A program bemenetként várja az indulási és érkezési célpontot (pl. `JFK -> LAX`). Kimenetként nem a legolcsóbb, hanem a **legmegbízhatóbb opciókat** adja vissza: megmutatja, hogy az adott útvonalon melyik légitársaságot és melyik napszakot érdemes választani a késés minimalizálása érdekében.

## 📊 Adatkészlet (Dataset)
A projekt a Kaggle-ről származó **[NYC Flights 2013](https://www.kaggle.com/)** adathalmazra épül.
- **Méret:** Több mint 300 000 belföldi járat adata.
- **Kiterjedés:** 2013-ban indult járatok New York három fő repülőteréről (JFK, LGA, EWR).
- **Legfontosabb attribútumok:** Indulási és érkezési késések (`dep_delay`, `arr_delay`), légitársaság (`carrier`), célállomás (`dest`), pontos dátum/időpont.

## ⚙️ Technikai megvalósítás
A projekt Python nyelven, **Pandas** és **NumPy** könyvtárak segítségével dolgozza fel az adatokat:

1. **Adattisztítás és Feature Engineering:** - A `year`, `month`, `day` és `hour` adatokból `datetime` objektumok képzése.
   - Járatok kategorizálása napszakok szerint (pl. *hajnal, délelőtt, délután, este*).
   - Hiányzó adatok és törölt járatok kezelése.
2. **Kockázati metrikák számítása:**
   - Átlagos késés meghatározása.
   - **Megbízhatósági index:** Késési valószínűség számítása NumPy segítségével az adott útvonalra és időszakra: `(15 percnél többet késő járatok száma) / (összes járat száma)`.
3. **Aggregáció és Rangsorolás:**
   - Adatok csoportosítása a `.groupby(['origin', 'dest', 'carrier', 'napszak'])` metódussal.
   - A kimenet rendezése a legkisebb kockázatú opcióktól a legrosszabbak felé.

## 🚀 Példa a működésre
Ha a felhasználó megadja a `JFK` (New York) -> `LAX` (Los Angeles) útvonalat, a program a következő aggregált ranglistát generálja:

| Rang | Minősítés | Légitársaság | Napszak | Késési esély | Átlagos késés |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 🥇 1. | **Javasolt** | Delta Airlines (DL) | Délelőtt | 12% | 5 perc |
| 🥈 2. | **Elfogadható** | American Airlines (AA) | Reggel | 18% | 11 perc |
| 🔴 3. | **Kockázatos** | United Airlines (UA) | Este | 42% | 35 perc |

Így az utazó már egy egyértelmű, adatokkal alátámasztott kockázati profil alapján tudja megvenni a jegyét.

## 💻 Telepítés és Futtatás (Helyi környezetben)

A projekt futtatásához [Conda](https://docs.conda.io/en/latest/) környezetkezelő javasolt.

1. **Repó klónozása:**
   ```bash
   git clone [https://github.com/FELHASZNALONEVED/adatelemzo-projekt.git](https://github.com/FELHASZNALONEVED/adatelemzo-projekt.git)
   cd adatelemzo-projekt