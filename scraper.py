import json
import boto3
import os
import requests
import uuid

def lambda_handler(event, context):
    nombre_tabla = os.environ["TABLE_NAME"]
    
    # 1. API Scraping: Apuntamos al backend (ArcGIS) que alimenta la web del IGP
    url = "https://ide.igp.gob.pe/arcgis/rest/services/monitoreocensis/SismosReportados/MapServer/0/query"
    
    # Configuramos los parámetros para pedir exactamente los 10 últimos sismos
    params = {
        "where": "1=1", # Traer todos los registros
        "outFields": "*", # Traer todas las columnas
        "orderByFields": "fecha DESC", # Ordenar del más reciente al más antiguo
        "resultRecordCount": "10", # Límite: Solo los 10 primeros
        "f": "json" # Pedir la respuesta en JSON
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        datos = response.json()
        
        # Validamos que la API haya devuelto información
        if 'features' not in datos or len(datos['features']) == 0:
            raise ValueError("La API del IGP no devolvió registros.")
            
        sismos_crudos = datos['features']
        
        # 2. Conectar a DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(nombre_tabla)
        sismos_guardados = []
        
        # 3. Iterar y Guardar
        for sismo in sismos_crudos:
            # ArcGIS guarda la data útil dentro de la llave 'attributes'
            atributos = sismo.get('attributes', {})
            
            id_sismo = str(uuid.uuid4())
            
            # Estructuramos el item para DynamoDB
            item = {
                'id_sismo': id_sismo,
                'sismo_datos': atributos # Guardamos todos los datos (magnitud, fecha, etc.)
            }
            
            table.put_item(Item=item)
            sismos_guardados.append(item)
            
        # 4. Retornar éxito
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
