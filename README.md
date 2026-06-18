# TravelMind — AI Travel Planner 🌍

Inteligentny planer podróży oparty na sztucznej inteligencji, wykorzystujący multi-agentową architekturę do tworzenia spersonalizowanych planów wycieczek.

## Funkcjonalności

- **Quiz podróżniczy** — ocena stylu podróży, tempa i preferencji
- **Personalizacja** — rekomendacje dopasowane do profilu podróżnika
- **Optymalizacja tras** — algorytm nearest-neighbor dla optymalnego zwiedzania
- **Guardrails** — walidacja atrakcji przez Google Maps (żadnych zmyślonych danych)
- **Interaktywna mapa** — wizualizacja trasy z numerowanymi markerami

## Architektura

```
Streamlit UI → LangGraph Orchestrator → 4 Agenty AI
                                          ├── Preference Agent (quiz → profil)
                                          ├── Discovery Agent (Google Places)
                                          ├── Logistics Agent (trasa, harmonogram)
                                          └── Validation Agent (guardrails)
```

## Tech Stack

| Komponent | Technologia |
|-----------|-------------|
| Frontend | Streamlit |
| LLM | Google Gemini |
| Mapy | Google Maps Places + Directions API |
| Orkiestracja | LangGraph |
| Walidacja | Pydantic v2 |

## Konfiguracja

### 1. Zainstaluj zależności

```bash
pip install -r requirements.txt
```

### 2. Utwórz plik `.env`

```bash
cp .env.example .env
```

Dodaj klucze API:

- **GOOGLE_MAPS_API_KEY** — z [Google Cloud Console](https://console.cloud.google.com/apis/credentials) (włącz Places API i Directions API)
- **GEMINI_API_KEY** — z [Google AI Studio](https://aistudio.google.com/apikey)

### 3. Uruchom aplikację

```bash
streamlit run app.py
```

## Struktura Projektu

```
Travel-planner/
├── app.py                  # Punkt wejścia Streamlit
├── config.py               # Konfiguracja
├── agents/                 # Agenci AI
│   ├── preference_agent.py # Quiz → profil podróżniczy
│   ├── discovery_agent.py  # Wyszukiwanie atrakcji
│   ├── logistics_agent.py  # Optymalizacja tras
│   └── validation_agent.py # Guardrails
├── graph/                  # LangGraph
│   ├── state.py            # Stan grafu
│   ├── nodes.py            # Węzły
│   └── builder.py          # Budowa grafu
├── services/               # Integracje zewnętrzne
│   ├── google_maps.py      # Google Maps API
│   └── gemini.py           # Gemini API
├── models/                 # Modele Pydantic
│   ├── profile.py          # Profil podróżnika
│   ├── attraction.py       # Atrakcja
│   └── itinerary.py        # Plan podróży
├── ui/                     # Komponenty Streamlit
│   ├── quiz_page.py        # Strona quizu
│   ├── results_page.py     # Strona wyników
│   ├── itinerary_page.py   # Strona planu
│   └── map_component.py    # Komponent mapy
└── tests/                  # Testy
```

## Testowanie

```bash
pytest tests/ -v
```

## Zasady (z Claude.md)

1. Priorytet dla danych Google Maps nad sugestiami modelu
2. Rekomendacje personalizowane profilem podróżnika
3. Plany muszą być realistyczne i wykonalne
4. Optymalizacja trasy jest obowiązkowa
5. Validation Agent zatwierdza każdy plan przed wyświetleniem
6. Interfejs wyświetla: plan, podsumowanie trasy, mapę, opisy atrakcji
7. Agenci rozszerzalni bez modyfikacji workflow
