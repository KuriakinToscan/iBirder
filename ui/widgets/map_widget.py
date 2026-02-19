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

    def update_map(self, lat, lon, zoom=5, add_marker=False, scientific_name=None):
        try:
            from core.gbif_client import get_gbif_taxon_key
            
            # Create Folium Map
            m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True, tiles=None)
            
            # Base Layers
            folium.TileLayer('OpenStreetMap', name='Mapa', control=True).add_to(m)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community', 
                name='Satélite', control=True
            ).add_to(m)

            # GBIF Layer (Always present for control visibility)
            gbif_url = ""
            attr_html = ""
            
            if scientific_name:
                taxon_key = get_gbif_taxon_key(scientific_name)
                if taxon_key:
                    # Attribution Link (Fixed: removed target='_blank' to work with interceptor)
                    species_url = f"https://www.gbif.org/species/{taxon_key}"
                    attr_html = f'<a href="{species_url}" style="font-weight:bold; color:#005fa8; text-decoration:none;">Dados: GBIF 🔗</a>'
                    
                    # v0.3.12: Reduced hexPerTile to 35 (larger hexagons)
                    gbif_url = f"https://api.gbif.org/v2/map/occurrence/density/{{z}}/{{x}}/{{y}}@1x.png?taxonKey={taxon_key}&basisOfRecord=HUMAN_OBSERVATION&basisOfRecord=OBSERVATION&bin=hex&hexPerTile=35&style=purpleYellow.poly"
            
            if not gbif_url:
                # Transparent tile for "Empty" state, so the layer control still shows "Dist. Geográfica"
                # This ensures the user sees the option is checked/unchecked even if invisible.
                gbif_url = "https://assets.ibis.ifi.unicamp.br/transparent.png" # Dummy transparent or just empty string might cause load error.
                # Better approach: Use a valid empty tile source or simply don't add if we can't force logic.
                # User asked: "option... should be always visible".
                # Folium doesn't easily allow "empty" layers in control without a valid tile source.
                # Let's use a common empty tile trick or just not add it if no data, BUT user insisted "always visible".
                # A 1x1 transparent pixel data URI is best but folium needs URL. 
                # Let's try adding it anyway with a safe fallback or just the same URL if we had a "default" density (not possible without taxon).
                
                # ALTERNATIVE: Use a generic taxon (like Aves) or just 1x1 transparent.
                # Since we don't have a reliable transparent tile URL handy without external dependency, 
                # and 'empty string' might break, let's skip adding the layer IF empty, 
                # UNLESS we find a way. 
                # Re-reading: "a opção... deve ser sempre visivel".
                # I will add the layer with a dummy valid URL that returns empty/transparent, 
                # OR just use a placeholder.
                # Let's use a known public transparent tile service or just skip logic change and assume 
                # "always visible" means "when data is available it stays checked". 
                # BUT "always visible" implies the checkbox is there even if no data.
                # Let's use a dummy transparent tile from a stable source or a data URI if folium supports it.
                # Folium supports data URIs.
                pass

            # Valid GBIF URL or Fallback for visibility
            if scientific_name and taxon_key: # Only add if we have actual data to show, otherwise it's confusing empty layer.
                 # Wait, user said "option should be always visible".
                 # If I add it with empty tiles, it will just show nothing.
                 # Let's stick to adding it when we have data for now, effectively "always visible" when relevant?
                 # No, user probably wants to toggle it ON/OFF even if they haven't searched yet? No, that makes no sense.
                 # User likely means: "Don't hide the layer control". The layer control is always added at the end.
                 # But the GBIF layer itself appears only if added.
                 # Let's try to add it with a dummy URL if no scientific name.
                 
                 pass # Logic below uses gbif_url logic.
            
            # REVISED STRATEGY: 
            # If we have a sci name, we show the density.
            # If NOT, we show nothing but maybe user wants the control to BE there.
            # I will implement: Always add the layer. If no key, use a transparent tile.
            # Transparent 1x1 png:
            transp_tile = "https://upload.wikimedia.org/wikipedia/commons/c/ca/1x1.png"
            
            final_url = gbif_url if gbif_url else transp_tile
            final_attr = attr_html if attr_html else "Dados: GBIF (Sem dados)"
            
            folium.TileLayer(
                tiles=final_url, 
                attr=final_attr, 
                name='Dist. Geográfica (GBIF)',
                overlay=True, 
                control=True, 
                show=True
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
