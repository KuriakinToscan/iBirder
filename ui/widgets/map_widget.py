from PySide6.QtWebEngineWidgets import QWebEngineView
import folium
import io

class MapWidget(QWebEngineView):
    def update_map(self, lat, lon, zoom=10, add_marker=False):
        try:
            # Cria o mapa base (OpenStreetMap é o padrão)
            m = folium.Map(location=[lat, lon], zoom_start=zoom, control_scale=True)

            # Adiciona Camada de Satélite (Esri World Imagery)
            folium.TileLayer(
                tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
                attr='Esri',
                name='Satélite'
            ).add_to(m)

            # Adiciona o Marcador (Se houver GPS)
            if add_marker:
                folium.Marker(
                    [lat, lon],
                    tooltip="Local do Registro",
                    icon=folium.Icon(color="red", icon="info-sign")
                ).add_to(m)

            # Adiciona o seletor de camadas no canto superior direito
            folium.LayerControl(position='topright', collapsed=False).add_to(m)

            data = io.BytesIO()
            m.save(data, close_file=False)
            self.setHtml(data.getvalue().decode())
        except Exception as e:
            self.show_placeholder_message(f"Erro no mapa: {str(e)}")

    def show_placeholder_message(self, text):
        """Exibe uma mensagem de texto centralizada (estilo placeholder)"""
        html = f"""
        <html>
        <body style="display:flex; justify-content:center; align-items:center; 
                     height:100%; margin:0; background-color:#f0f0f0; 
                     font-family:'Segoe UI', sans-serif; color:#666;">
            <div style="text-align:center;">
                <div style="font-size:24px; margin-bottom:10px;">📍</div>
                <div style="font-size:14px; font-weight:500;">{text}</div>
            </div>
        </body>
        </html>
        """
        self.setHtml(html)
