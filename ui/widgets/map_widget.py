from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtGui import QDesktopServices
from PySide6.QtCore import QUrl
import folium
import io

class ExternalLinkPage(QWebEnginePage):
    def acceptNavigationRequest(self, url, _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True

class MapWidget(QWebEngineView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPage(ExternalLinkPage(self)) # Intercepta links to open in default browser

    def show_placeholder_message(self, message):
        html = f"""
        <html>
        <body style="display:flex; justify-content:center; align-items:center; height:100%; margin:0; font-family:'Segoe UI', sans-serif; background-color:#f0f2f5; color:#6b7280;">
            <div style="text-align:center;">
                <div style="font-size:14px;">{message}</div>
            </div>
        </body>
        </html>
        """
        self.setHtml(html)

    def update_map(self, lat, lon, zoom=10, add_marker=False, scientific_name=None):
        try:
            from core.gbif_client import get_gbif_taxon_key
            
            # Create Folium Map
            m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True, tiles=None)
            
            # Base Layers
            folium.TileLayer('OpenStreetMap', name='Mapa', control=True).add_to(m)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri', name='Satélite', control=True
            ).add_to(m)

            # GBIF Layer (Overlay)
            if scientific_name:
                taxon_key = get_gbif_taxon_key(scientific_name)
                if taxon_key:
                    # Attribution Link
                    species_url = f"https://www.gbif.org/species/{taxon_key}"
                    attr_html = f'<a href="{species_url}" target="_blank" style="font-weight:bold; color:#005fa8; text-decoration:none;">Dados: GBIF 🔗</a>'
                    
                    gbif_url = f"https://api.gbif.org/v2/map/occurrence/density/{{z}}/{{x}}/{{y}}@1x.png?taxonKey={taxon_key}&bin=hex&hexPerTile=30&style=classic.poly"
                    
                    folium.TileLayer(
                        tiles=gbif_url, attr=attr_html, name='Dist. Geográfica (GBIF)',
                        overlay=True, control=True, show=True
                    ).add_to(m)

            if add_marker:
                folium.Marker(
                    [lat, lon], 
                    icon=folium.Icon(color="red", icon="info-sign"),
                    tooltip="Local da Foto"
                ).add_to(m)

            folium.LayerControl(position='topright', collapsed=False).add_to(m)
            
            data = io.BytesIO()
            m.save(data, close_file=False)
            self.setHtml(data.getvalue().decode())
            
        except Exception as e:
            self.setHtml(f"<html><body>Error loading map: {e}</body></html>")
