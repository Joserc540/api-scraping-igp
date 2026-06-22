import json
import boto3
import os
import requests
import uuid
from decimal import Decimal # 1. Importamos la librería Decimal

def lambda_handler(event, context):
    nombre_tabla = os.environ["TABLE_NAME"]
    
    # API Scraping: Apuntamos al backend (ArcGIS) que alimenta la web del IGP
    url = "https://ide.igp.gob.pe/arcgis/rest/services/monitoreocensis/SismosReportados/MapServer/0/query"
    
    params = {
        "where": "1=1", 
        "outFields": "*", 
        "orderByFields": "fecha DESC", 
        "resultRecordCount": "10", 
        "f": "json" 
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        datos = response.json()
        
        if 'features' not in datos or len(datos['features']) == 0:
            raise ValueError("La API del IGP no devolvió registros.")
            
        sismos_crudos = datos['features']
        
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(nombre_tabla)
        sismos_guardados = []
        
        for sismo in sismos_crudos:
            atributos = sismo.get('attributes', {})
            id_sismo = str(uuid.uuid4())
            
            # 2. EL TRUCO PARA DYNAMODB:
            # Convertimos el diccionario a un texto JSON y lo volvemos a leer, 
            # pero forzando a que todo "float" se convierta en "Decimal" para que AWS lo acepte.
            atributos_para_dynamo = json.loads(json.dumps(atributos), parse_float=Decimal)
            
            item = {
                'id_sismo': id_sismo,
                'sismo_datos': atributos_para_dynamo # Mandamos los Decimals a la base de datos
            }
            
            table.put_item(Item=item)
            
            # Para la respuesta al cliente (Postman), guardamos los atributos originales 
            # porque json.dumps() no soporta los objetos Decimal.
            sismos_guardados.append({
                'id_sismo': id_sismo,
                'sismo_datos': atributos 
            })
            
        return {
            'statusCode': 200,
            'body': json.dumps({
                'mensaje': 'API Scraping del IGP exitoso',
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
