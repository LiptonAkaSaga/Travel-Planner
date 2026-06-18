"""Map component — interactive Folium map with route visualization."""

import streamlit as st
import folium
from folium.plugins import AntPath
from streamlit_folium import st_folium
from models.itinerary import Itinerary, DayPlan


def render_map(itinerary: Itinerary) -> None:
    """Render an interactive map with attractions and routes.

    Args:
        itinerary: The itinerary to visualize on the map.
    """
    if not itinerary.days:
        st.warning("Brak danych do wyświetlenia na mapie.")
        return

    # Calculate map center from all attractions
    all_lats: list[float] = []
    all_lngs: list[float] = []
    for day in itinerary.days:
        for attr in day.attractions:
            all_lats.append(attr.lat)
            all_lngs.append(attr.lng)

    if not all_lats:
        return

    center_lat = sum(all_lats) / len(all_lats)
    center_lng = sum(all_lngs) / len(all_lngs)

    # Create map
    m = folium.Map(location=[center_lat, center_lng], zoom_start=13)

    # Color palette for days
    day_colors = [
        "#e74c3c",  # red
        "#3498db",  # blue
        "#2ecc71",  # green
        "#f39c12",  # orange
        "#9b59b6",  # purple
        "#1abc9c",  # teal
        "#e67e22",  # dark orange
        "#34495e",  # dark blue
    ]

    for day in itinerary.days:
        color = day_colors[(day.day_number - 1) % len(day_colors)]

        # Add markers for each attraction
        for i, attr in enumerate(day.attractions):
            popup_html = f"""
            <b>Dzień {day.day_number} | {i + 1}. {attr.name}</b><br>
            ⭐ {attr.rating}/5 ({attr.user_ratings_total} opinii)<br>
            📍 {attr.address}<br>
            ⏱️ {attr.visit_duration_minutes} min
            """
            if attr.description:
                popup_html += f"<br>📝 {attr.description[:100]}..."

            folium.Marker(
                location=[attr.lat, attr.lng],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"D{day.day_number}.{i + 1}: {attr.name}",
                icon=folium.Icon(color="red" if day.day_number == 1 else "blue", icon="info-sign"),
            ).add_to(m)

            # Add day number label
            folium.Marker(
                location=[attr.lat, attr.lng],
                icon=folium.DivIcon(
                    html=f'<div style="font-size: 12px; font-weight: bold; color: white; '
                    f'background: {color}; border-radius: 50%; width: 24px; height: 24px; '
                    f'display: flex; align-items: center; justify-content: center;">'
                    f"{i + 1}</div>",
                    icon_size=(24, 24),
                    icon_anchor=(12, 12),
                ),
            ).add_to(m)

        # Draw route lines
        if len(day.attractions) > 1:
            route_points = [[a.lat, a.lng] for a in day.attractions]
            AntPath(
                locations=route_points,
                color=color,
                weight=3,
                opacity=0.8,
                dash_array=[10, 20],
            ).add_to(m)

    # Render in Streamlit
    st_folium(m, width=725, height=500)
