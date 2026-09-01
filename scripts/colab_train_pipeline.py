# iBirder Neotropical Model Training Pipeline
# Treinamento da IA especializada nas aves do Brasil e América do Sul

import tensorflow as tf
from tensorflow.keras import layers, models
import matplotlib.pyplot as plt

print("TensorFlow Version:", tf.__version__)
print("GPUs Disponíveis:", tf.config.list_physical_devices('GPU'))

# 1. Configurações Globais
IMG_SIZE = (224, 224)
BATCH_SIZE = 32
EPOCHS = 15

# 2. Pipeline de Data Augmentation
data_augmentation = tf.keras.Sequential([
    layers.RandomFlip("horizontal"),
    layers.RandomRotation(0.15),
    layers.RandomZoom(0.15),
    layers.RandomContrast(0.2),
    layers.RandomBrightness(0.2)
])

# 3. Construção do Modelo (Transfer Learning com EfficientNetV2-Small)
base_model = tf.keras.applications.EfficientNetV2S(
    input_shape=(224, 224, 3),
    include_top=False,
    weights='imagenet'
)
base_model.trainable = True # Fine-tuning completo das camadas convolucionais

model = models.Sequential([
    layers.Input(shape=(224, 224, 3)),
    data_augmentation,
    base_model,
    layers.GlobalAveragePooling2D(),
    layers.Dropout(0.3),
    layers.Dense(1980, activation='softmax') # 1.980+ espécies de aves brasileiras
])

model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=1e-4),
    loss='categorical_crossentropy',
    metrics=['accuracy', tf.keras.metrics.TopKCategoricalAccuracy(k=3, name='top_3_accuracy')]
)

model.summary()

# 4. Exportação e Quantização para TFLite (FP16 / Dynamic INT8)
def export_tflite(keras_model, output_path):
    converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16] # Quantização FP16 para reduzir 50% de tamanho sem perda
    tflite_model = converter.convert()

    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    print(f"Modelo TFLite salvo em {output_path} ({len(tflite_model)/(1024*1024):.2f} MB)")

# export_tflite(model, 'ibirder_aves_brasil_v1.tflite')
