import json
import boto3
import os
import requests
from bs4 import BeautifulSoup
import uuid

def lambda_handler(event, context):
    url = "https://ultimosismo.igp.gob.pe/productos/reportes-sismicos"
    nombre_tabla = os.environ["TABLE_NAME"]
    
    try:
        # 1. Hacer la petición HTTP a la web del IGP
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Lanza un error si la página no responde con 200 OK
        
        # 2. Parsear el HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Encontrar la tabla de sismos
        tabla = soup.find('table')
        if not tabla:
            raise ValueError("No se encontró ninguna tabla de sismos en la página web.")
            
        # Extraer las filas (<tr>). Buscamos dentro de <tbody> si existe, o ignoramos la cabecera
        tbody = tabla.find('tbody')
        filas = tbody.find_all('tr') if tbody else tabla.find_all('tr')[1:]
        
        # Seleccionar solo los 10 últimos sismos (las 10 primeras filas)
        ultimos_10_sismos = filas[:10]
        
        # 4. Conectar a DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(nombre_tabla)
        
        sismos_guardados = []
        
        # 5. Iterar sobre las 10 filas, extraer columnas y guardar
        for fila in ultimos_10_sismos:
            # Encontramos todas las celdas (<td>) de la fila actual
            columnas = fila.find_all('td')
            
            # Limpiamos los textos (quitamos espacios en blanco extra)
            datos_limpios = [col.text.strip() for col in columnas if col.text.strip()]
            
            if len(datos_limpios) > 0:
                id_sismo = str(uuid.uuid4())
                
                # Armamos el item JSON para DynamoDB
                item = {
                    'id_sismo': id_sismo,
                    'detalle': datos_limpios
                }
                
                # Insertar en la base de datos
                table.put_item(Item=item)
                sismos_guardados.append(item)
                
        # 6. Retornar éxito
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensaje': 'Scraping del IGP exitoso y guardado en DynamoDB',
                'cantidad_registros': len(sismos_guardados),
                'sismos_recientes': sismos_guardados
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"[ERROR] Fallo en el scraping: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Error interno', 'detalle': str(e)})
        }