# Symulacja Trebusza 🏰

Interaktywna symulacja fizyczna trebusza napisana w języku Python przy użyciu biblioteki `pygame`, stworzona jako projekt edukacyjny z fizyki. Program wizualizuje mechanikę maszyny oblężniczej i pozwala na badanie wpływu różnych parametrów konstrukcyjnych na ostateczny zasięg rzutu kuli.

<img width="1280" height="757" alt="image" src="https://github.com/user-attachments/assets/2347fecc-18a2-4f8f-8287-9a092927664a" />

## ✨ Główne funkcje

* **Symulacja w czasie rzeczywistym:** Obliczenia fizyczne i renderowanie odbywają się w 60 klatkach na sekundę.
* **Interaktywny panel sterowania:** Możliwość płynnej zmiany 10 różnych parametrów za pomocą suwaków (m.in. masy, długości ramion, długość procy, kąty zwolnienia).
* **Dynamiczna kamera:** Kadr automatycznie dostosowuje się i oddala, aby śledzić cały lot pocisku i pomieścić pełną trajektorię.
* **Dane telemetryczne na żywo:** Program na bieżąco oblicza i wyświetla:
  * Dystans lotu (w metrach)
  * Prędkość wyrzutu (w m/s)
  * Prędkość uderzenia w ziemię (w m/s)
* **Wizualizacja trajektorii:** Wyświetlanie rzeczywistej drogi przebytej przez kulę oraz natychmiastowe rysowanie przewidywanego toru lotu balistycznego.

## 🧮 Zastosowana fizyka

Program nie korzysta z gotowych silników fizycznych (jak np. Box2D) – cała matematyka została zaimplementowana od zera w kodzie:

* **Ruch obrotowy:** Obliczanie momentu bezwładności dla ramienia (traktowanego jako pręt) i sumowanie momentów sił (od grawitacji kuli i naciągu linki przeciwwagi).
* **Układ przeciwwagi:** Symulowany jako wahadło podwieszone do poruszającego się punktu (wymagało to uwzględnienia przyspieszenia haka w równaniach wahadła).
* **Kinematyka procy:** Proca jest symulowana poprzez rzutowanie wektorów prędkości względnej i nałożenie twardych więzów odległości.
* **Całkowanie numeryczne:** Do przeliczania stanu symulacji w czasie (pozycja, prędkość, przyspieszenie) zastosowano metodę pół-niejawnego Eulera (Semi-implicit Euler integration), która zapewnia dobrą stabilność numeryczną w prostych układach fizycznych.
* **Rzut ukośny:** Lot swobodny pocisku po zwolnieniu z procy odbywa się pod wpływem grawitacji (bez uwzględniania oporu powietrza).

## 🚀 Wymagania i instalacja

Do uruchomienia projektu wymagany jest **Python 3.x** oraz biblioteki **pygame** i **math**.

1. Sklonuj repozytorium:
   ```bash
   git clone https://github.com/Gucianoski/Symulator-Trebusza-Igor-Majchrzak.git
   cd trebusz-symulacja
