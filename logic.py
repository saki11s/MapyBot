import sqlite3
from config import * 
import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import matplotlib.patheffects as mpatheffects 
import cartopy.crs as ccrs
import cartopy.feature as cfeature 

class DB_Map():
    def __init__(self, database):
        self.database = database
    
    def create_user_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS users_cities (
                                user_id INTEGER,
                                city_id TEXT,
                                FOREIGN KEY(city_id) REFERENCES cities(id)
                            )''')
            conn.commit()

    def create_user_settings_table(self):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS user_settings (
                                user_id INTEGER PRIMARY KEY,
                                marker_color TEXT DEFAULT 'red'
                            )''')
            conn.commit()

    def add_city(self,user_id, city_name ):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cities WHERE city=?", (city_name,))
            city_data = cursor.fetchone()
            if city_data:
                city_id = city_data[0]  
                cursor.execute("SELECT 1 FROM users_cities WHERE user_id=? AND city_id=?", (user_id, city_id))
                if cursor.fetchone():
                    return 2 
                conn.execute('INSERT INTO users_cities VALUES (?, ?)', (user_id, city_id))
                conn.commit()
                return 1 
            else:
                return 0 
            
    def select_cities(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT cities.city 
                            FROM users_cities  
                            JOIN cities ON users_cities.city_id = cities.id
                            WHERE users_cities.user_id = ?''', (user_id,))
            cities = [row[0] for row in cursor.fetchall()]
            return cities

    def get_coordinates(self, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('''SELECT lat, lng FROM cities WHERE city = ?''', (city_name,))
            coordinates = cursor.fetchone()
            return coordinates

    def set_user_marker_color(self, user_id, color):
        conn = sqlite3.connect(self.database)
        with conn:
            conn.execute('INSERT OR REPLACE INTO user_settings (user_id, marker_color) VALUES (?, ?)', (user_id, color))
            conn.commit()
            return True

    def get_user_marker_color(self, user_id):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute('SELECT marker_color FROM user_settings WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else 'red'

    def create_grapf(self, path_to_save, city_names_list, marker_color='red'):
        """
        Создает карту с отмеченными городами.
        path_to_save: Путь для сохранения изображения карты.
        city_names_list: Список названий городов для отображения.
        marker_color: Цвет маркеров для городов (по умолчанию 'red').
        Возвращает True, если хотя бы один город был успешно нанесен на карту, иначе False.
        """
        fig = plt.figure(figsize=(14, 10)) 
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree()) 

        LAND_COLOR = '#EFEAE0'  
        OCEAN_COLOR = '#E0F2F7' 
        BORDER_COLOR = '#B0B0B0' 
        COASTLINE_COLOR = '#808080' 
        RIVER_COLOR = '#90C0D0' 
        LAKE_COLOR = '#A0D0E0' 

        ax.add_feature(cfeature.LAND.with_scale('10m'), edgecolor='none', facecolor=LAND_COLOR)
        ax.add_feature(cfeature.OCEAN.with_scale('10m'), facecolor=OCEAN_COLOR)
        ax.add_feature(cfeature.COASTLINE.with_scale('10m'), linewidth=0.7, edgecolor=COASTLINE_COLOR)
        ax.add_feature(cfeature.BORDERS.with_scale('10m'), linestyle=':', linewidth=0.5, edgecolor=BORDER_COLOR)
        ax.add_feature(cfeature.LAKES.with_scale('10m'), alpha=0.8, facecolor=LAKE_COLOR, edgecolor=BORDER_COLOR, linewidth=0.3)
        ax.add_feature(cfeature.RIVERS.with_scale('10m'), alpha=0.6, edgecolor=RIVER_COLOR, linewidth=0.4)
        ax.add_feature(cfeature.STATES.with_scale('10m'), linestyle=':', edgecolor=BORDER_COLOR, linewidth=0.3)
        
        ax.set_frame_on(False) 

        plotted_cities_coords = []
        city_plot_details = [] 

        for city_name in city_names_list:
            coords = self.get_coordinates(city_name)
            if coords:
                lat, lon = coords
                plotted_cities_coords.append((lon, lat)) 
                city_plot_details.append({'name': city_name, 'lon': lon, 'lat': lat})
            else:
                print(f"Координаты для города '{city_name}' не найдены.")
        
        if not plotted_cities_coords:
            plt.close(fig) 
            return False

        if len(plotted_cities_coords) == 1:
            lon, lat = plotted_cities_coords[0]
            extent_padding = 4 
            ax.set_extent([lon - extent_padding, lon + extent_padding, 
                           lat - extent_padding, lat + extent_padding], crs=ccrs.PlateCarree())
        elif len(plotted_cities_coords) > 1:
            min_lon = min(c[0] for c in plotted_cities_coords)
            max_lon = max(c[0] for c in plotted_cities_coords)
            min_lat = min(c[1] for c in plotted_cities_coords)
            max_lat = max(c[1] for c in plotted_cities_coords)
            padding_lon = max((max_lon - min_lon) * 0.2, 1.5) 
            padding_lat = max((max_lat - min_lat) * 0.2, 1.5)
            ax.set_extent([min_lon - padding_lon, max_lon + padding_lon, 
                           min_lat - padding_lat, max_lat + padding_lat], crs=ccrs.PlateCarree())
        else:
            ax.set_global()

        for city_detail in city_plot_details:
            ax.plot(city_detail['lon'], city_detail['lat'], 
                    'o', 
                    color=marker_color,
                    markersize=8, 
                    markeredgecolor='white', 
                    markeredgewidth=1.5, 
                    transform=ccrs.Geodetic()) 
            ax.text(city_detail['lon'] + 0.1, city_detail['lat'] + 0.1, 
                    city_detail['name'], 
                    transform=ccrs.Geodetic(), 
                    fontsize=10, 
                    color='black', 
                    verticalalignment='bottom', 
                    horizontalalignment='left',
                    path_effects=[mpatheffects.withStroke(linewidth=3, foreground='white', alpha=0.9)]) 

        gl = ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
                          linewidth=0.7, color='gray', alpha=0.4, linestyle='--') 
        gl.top_labels = False 
        gl.right_labels = False 
        gl.xlabel_style = {'size': 9, 'color': 'gray'}
        gl.ylabel_style = {'size': 9, 'color': 'gray'}
        
        if len(city_names_list) == 1:
             plt.title(f"Карта города: {city_names_list[0]}", fontsize=16, pad=15, color='black') 
        elif len(city_names_list) > 1:
             plt.title("Карта твоих городов", fontsize=16, pad=15, color='black')

        plt.savefig(path_to_save, bbox_inches='tight', dpi=300) 
        plt.close(fig) 
        return True
        
    def delete_city_from_user_list(self, user_id, city_name):
        conn = sqlite3.connect(self.database)
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM cities WHERE city=?", (city_name,))
            city_data = cursor.fetchone()
            
            if not city_data:
                print(f"Город {city_name} не найден в основной таблице 'cities' при попытке удаления.")
                return False 

            city_id_to_delete = city_data[0]
            
            result = cursor.execute('DELETE FROM users_cities WHERE user_id = ? AND city_id = ?', 
                                    (user_id, city_id_to_delete))
            conn.commit()
            
            return result.rowcount > 0

    def draw_distance(self, city1, city2):
        pass


if __name__=="__main__":
    manager = DB_Map(DATABASE)
    manager.create_user_table()
    manager.create_user_settings_table()