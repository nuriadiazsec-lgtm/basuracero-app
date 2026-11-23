import os
import numpy as np
from tensorflow.keras.applications.mobilenet_v2 import MobileNetV2, preprocess_input, decode_predictions
from tensorflow.keras.preprocessing import image

print("Cargando modelo de IA...")
model = MobileNetV2(weights='imagenet')

def analizar_imagen_ia(img_path):
    try:
        img = image.load_img(img_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = preprocess_input(x)
        
        preds = model.predict(x)
        resultados = decode_predictions(preds, top=3)[0]
        
        mejor_resultado = resultados[0]
        etiqueta_ingles = mejor_resultado[1].lower()
        certeza = mejor_resultado[2] * 100
        
        # Diccionario AMPLIADO
        traducciones = {
            "ashcan": "Bolsas y contenedores", "plastic_bag": "Bolsas de plástico",
            "water_bottle": "Botellas de plástico", "pop_bottle": "Botellas de plástico",
            "wine_bottle": "Vidrio", "beer_bottle": "Vidrio",
            "beer_glass": "Vidrio roto", "carton": "Cartón y papel", 
            "envelope": "Papel / Cartón", "paper_towel": "Papel",
            "toilet_tissue": "Papel", "diaper": "Residuo sanitario",
            "shopping_cart": "Chatarra / Metal", "can": "Lata de metal",
            "bucket": "Plásticos duros", "barrow": "Escombros y restos",
            "pot": "Escombros / Cerámica", "crate": "Madera / Cajones",
            "match": "Residuos pequeños", "packet": "Envoltorios"
        }
        
        # LÓGICA DE CLASIFICACIÓN Y ACUMULACIÓN MEJORADA
        if certeza < 20.0 or etiqueta_ingles not in traducciones:
            tipo_basura = "Basural mixto (varios materiales)"
            # Si el modelo se confunde mucho, suele ser una pila de cosas mezcladas
            nivel = "Alta acumulación - Gran cantidad de residuos dispersos o basural crónico."
        else:
            tipo_basura = traducciones[etiqueta_ingles]
            
            # Si ve un objeto súper claro, suele ser poca basura. Si le cuesta, es más volumen.
            if certeza > 70: 
                nivel = "Baja acumulación - Elementos aislados o poca cantidad."
            elif certeza > 40: 
                nivel = "Acumulación moderada - Foco de basura en crecimiento."
            else: 
                nivel = "Alta acumulación - Gran cantidad de residuos dispersos."
            
        return {
            "tipo": f"{tipo_basura} (Certeza IA: {certeza:.1f}%)",
            "nivel": nivel,
            "similitud": "Análisis completado."
        }
    except Exception as e:
        return {"tipo": "Error al procesar", "nivel": "Desconocido", "similitud": "Desconocido"}