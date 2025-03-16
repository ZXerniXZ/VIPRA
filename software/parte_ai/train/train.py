from ultralytics import YOLO
import os
import yaml
import json
import shutil
import torch
from sklearn.model_selection import train_test_split
import sys
import wandb
from datetime import datetime
from config import PATHS

# Aumenta il limite di ricorsione
sys.setrecursionlimit(10000)

def verify_cuda():
    print("\n=== Verifica CUDA ===")
    print(f"PyTorch versione: {torch.__version__}")
    print(f"CUDA è disponibile: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA versione: {torch.version.cuda}")
        print(f"GPU in uso: {torch.cuda.get_device_name(0)}")
        print(f"Numero di GPU disponibili: {torch.cuda.device_count()}")
        # Test semplice per verificare che CUDA funzioni
        x = torch.tensor([1.0, 2.0, 3.0]).cuda()
        print(f"Test CUDA - Device del tensore: {x.device}")
    print("===================\n")

# Chiama la funzione all'inizio
verify_cuda()

print(f"CUDA è disponibile: {torch.cuda.is_available()}")
print(f"Dispositivo corrente: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")

class WandbLogger:
    def __init__(self):
        self.current_epoch = 0

    def log_metrics(self, metrics, step=None):
        wandb.log(metrics, step=step)

class ModelTrainer:
    def __init__(self, project_name="RoadDamageDetection"):
        self.data_dir = PATHS['video_dir']
        self.annotations_file = PATHS['annotations']
        self.dataset_dir = 'dataset'
        self.images_dir = os.path.join(self.dataset_dir, 'images')
        self.labels_dir = os.path.join(self.dataset_dir, 'labels')
        self.project_name = project_name

        # Determina il device disponibile
        self.device = self._get_device()
        print(f"Dispositivo utilizzato per il training: {self.device}")

        # Inizializza wandb
        self.init_wandb()
        self.wandb_logger = WandbLogger()
        self.batch_count = 0
        self.batch_counter = 0
        self.log_frequency = 10  # Log ogni 10 batch
        self.metrics_buffer = {}  # Buffer per accumulare le metriche

    def init_wandb(self):
        try:
            import wandb

            # Configurazione più dettagliata
            wandb_config = {
                "architecture": "YOLOv8n",
                "dataset": "RoadDamage",
                "device": self.device,
                "epochs": 100,
                "batch_size": 8,
                "image_size": 640,
                "optimizer": "auto",
                "learning_rate": "auto",
                "augmentation": True
            }

            # Inizializzazione con opzioni essenziali
            self.wandb_run = wandb.init(
                project=self.project_name,
                name=f"train_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                config=wandb_config,
                settings=wandb.Settings(start_method="thread"),
                resume="allow"
            )

            print(f"WandB inizializzato. URL: {wandb.run.get_url()}")

        except Exception as e:
            print(f"ERRORE CRITICO nell'inizializzazione di wandb: {str(e)}")
            import traceback
            traceback.print_exc()

    def _get_device(self):
        """Determina il miglior device disponibile per il training"""
        if torch.cuda.is_available():
            cuda_device = torch.device('cuda')
            print(f"CUDA è disponibile!")
            print(f"GPU in uso: {torch.cuda.get_device_name(0)}")
            print(f"Numero di GPU disponibili: {torch.cuda.device_count()}")
            print(f"Memoria GPU totale: {torch.cuda.get_device_properties(0).total_memory / 1024**2:.0f} MB")
            return 'cuda'
        elif torch.backends.mps.is_available():
            print("MPS (Metal Performance Shaders) disponibile per Mac M1/M2")
            return 'mps'
        else:
            print("CUDA non disponibile, usando CPU")
            return 'cpu'

    def prepare_dataset(self):
        """Prepara il dataset per il training"""
        try:
            print("Preparazione dataset...")
            print(f"Caricamento annotazioni da: {self.annotations_file}")

            # Carica le annotazioni COCO
            with open(self.annotations_file, 'r') as f:
                coco_data = json.load(f)

                # Aggiorna le categorie con i nomi corretti
                coco_data['categories'] = [
                    {'id': 1, 'name': 'longitudinal'},  # Fessura longitudinale
                    {'id': 2, 'name': 'transverse'},    # Fessura trasversale
                    {'id': 3, 'name': 'alligator'},     # Pattern a pelle di coccodrillo
                    {'id': 4, 'name': 'pothole'},       # Buca
                    {'id': 5, 'name': 'manhole'},      # Dosso stradale
                    {'id': 6, 'name': 'roadbump'}        # Tombino
                ]

                # Crea un mapping per aggiornare le category_id nelle annotazioni
                category_mapping = {
                    'D00': 1,  # longitudinal
                    'D10': 2,  # transverse
                    'D20': 3,  # alligator
                    'D40': 4,  # pothole
                    'D50': 5,  
                    'D60': 6   # roadbump
                }

                # Aggiorna le category_id nelle annotazioni
                for ann in coco_data['annotations']:
                    old_category = next((cat['name'] for cat in coco_data['categories'] 
                                       if cat['id'] == ann['category_id']), None)
                    if old_category in category_mapping:
                        ann['category_id'] = category_mapping[old_category]

                print("\n=== Categorie aggiornate ===")
                for cat in coco_data['categories']:
                    print(f"ID: {cat['id']} - Nome: {cat['name']}")
                print("==========================\n")

            # Crea le directory necessarie
            os.makedirs(self.dataset_dir, exist_ok=True)
            for split in ['train', 'val', 'test']:
                os.makedirs(os.path.join(self.images_dir, split), exist_ok=True)
                os.makedirs(os.path.join(self.labels_dir, split), exist_ok=True)

            # Converti le annotazioni COCO in formato YOLO
            image_annotations = {}
            for ann in coco_data['annotations']:
                image_id = ann['image_id']
                if image_id not in image_annotations:
                    image_annotations[image_id] = []

                # Trova l'immagine corrispondente
                img_info = next((img for img in coco_data['images'] if img['id'] == image_id), None)

                if img_info is None:
                    continue

                # Modifica il percorso per usare frames_dir
                img_path = os.path.join(PATHS['frames_dir'], img_info['file_name'])

                img_width = img_info['width']
                img_height = img_info['height']

                bbox = ann['bbox']
                x_center = (bbox[0] + bbox[2]/2) / img_width
                y_center = (bbox[1] + bbox[3]/2) / img_height
                width = bbox[2] / img_width
                height = bbox[3] / img_height

                category_id = ann['category_id'] - 1

                image_annotations[image_id].append(f"{category_id} {x_center} {y_center} {width} {height}")

            # Split dataset
            all_images = coco_data['images']
            train_imgs, temp_imgs = train_test_split(all_images, test_size=0.3, random_state=42)
            val_imgs, test_imgs = train_test_split(temp_imgs, test_size=0.5, random_state=42)

            def process_split(images, split):
                for img in images:
                    # Costruisci il percorso corretto dell'immagine
                    src_path = os.path.join(PATHS['frames_dir'], img['file_name'])

                    if not os.path.exists(src_path):
                        print(f"Warning: Image not found: {src_path}")
                        continue

                    dst_path = os.path.join(self.images_dir, split, img['file_name'])
                    shutil.copy2(src_path, dst_path)

                    if img['id'] in image_annotations:
                        label_path = os.path.join(self.labels_dir, split, 
                                                os.path.splitext(img['file_name'])[0] + '.txt')
                        with open(label_path, 'w') as f:
                            f.write('\n'.join(image_annotations[img['id']]))

            print("Processamento split train...")
            process_split(train_imgs, 'train')
            print("Processamento split validation...")
            process_split(val_imgs, 'val')
            print("Processamento split test...")
            process_split(test_imgs, 'test')

            # Modifica qui: salva data.yaml nella directory del dataset
            data_yaml_path = os.path.join(self.dataset_dir, 'data.yaml')
            dataset_yaml = {
                'path': os.path.abspath(self.dataset_dir),
                'train': 'images/train',
                'val': 'images/val',
                'test': 'images/test',
                'nc': len(coco_data['categories']),
                'names': [cat['name'] for cat in coco_data['categories']]
            }

            # Salva il file data.yaml nella directory del dataset
            with open(data_yaml_path, 'w') as f:
                yaml.dump(dataset_yaml, f, default_flow_style=False)

            print(f"File data.yaml salvato in: {data_yaml_path}")

            # Aggiorna la configurazione wandb solo se è stato inizializzato
            if wandb.run is not None:
                dataset_stats = {
                    'dataset/train_images': len(train_imgs),
                    'dataset/val_images': len(val_imgs),
                    'dataset/test_images': len(test_imgs),
                    'dataset/total_images': len(all_images),
                    'dataset/num_classes': len(coco_data['categories'])
                }
                wandb.config.update(dataset_stats, allow_val_change=True)

                # Log delle statistiche come metriche
                wandb.log(dataset_stats)

                print("Statistiche dataset aggiornate su wandb")

            # Log sample images with annotations
            self.log_sample_images(train_imgs[:5], image_annotations)

            # Aggiungi il riepilogo del dataset
            print("\n=== Riepilogo Dataset ===")
            print(f"Totale immagini: {len(coco_data['images'])}")
            print(f"Totale annotazioni: {len(coco_data['annotations'])}")
            print("\nAnnotazioni per categoria:")
            category_counts = {}
            for ann in coco_data['annotations']:
                cat_name = next(cat['name'] for cat in coco_data['categories'] if cat['id'] == ann['category_id'])
                category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

            for cat_name, count in category_counts.items():
                print(f"- {cat_name}: {count} annotazioni")
            print("=====================\n")

            print("Dataset preparato con successo!")
            return True

        except Exception as e:
            print(f"Errore durante la preparazione del dataset: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def log_sample_images(self, images, annotations):
        """Log alcune immagini di esempio con le loro annotazioni"""
        try:
            class_labels = self._get_class_labels()  # Ottieni il dizionario delle classi

            for img in images:
                img_path = os.path.join(PATHS['frames_dir'], img['file_name'])

                if os.path.exists(img_path):
                    # Crea un'immagine wandb con le annotazioni
                    image = wandb.Image(
                        img_path,
                        boxes={
                            "predictions": {
                                "box_data": self._get_box_data(img['id'], annotations),
                                "class_labels": class_labels  # Usa il dizionario delle classi
                            }
                        }
                    )
                    wandb.log({"sample_images": image})
                else:
                    print(f"Immagine non trovata: {img_path}")
        except Exception as e:
            print(f"Errore nel logging delle immagini: {str(e)}")
            import traceback
            traceback.print_exc()

    def _get_box_data(self, image_id, annotations):
        """Converte le annotazioni nel formato richiesto da wandb"""
        try:
            if image_id not in annotations:
                return []

            box_data = []
            for ann in annotations[image_id]:
                class_id, x_center, y_center, width, height = map(float, ann.split())
                box_data.append({
                    "position": {
                        "middle": [float(x_center), float(y_center)],
                        "width": float(width),
                        "height": float(height)
                    },
                    "class_id": int(class_id),
                    "domain": "pixel"
                })
            return box_data
        except Exception as e:
            print(f"Errore nella conversione delle annotazioni: {str(e)}")
            return []

    def _get_class_labels(self):
        """Restituisce le etichette delle classi come dizionario"""
        try:
            with open(os.path.join(self.dataset_dir, 'data.yaml'), 'r') as f:
                dataset_config = yaml.safe_load(f)
                # Converti la lista in dizionario con indici come chiavi
                return {i: name for i, name in enumerate(dataset_config['names'])}
        except Exception as e:
            print(f"Errore nel caricamento delle classi: {e}")
            return {}

    def on_train_batch_end(self, trainer):
        try:
            if hasattr(trainer, 'tloss'):
                # Incrementa il contatore dei batch
                self.batch_counter += 1

                # Gestione sicura dei tensori
                def safe_tensor_to_float(tensor, name='unknown'):
                    try:
                        if torch.is_tensor(tensor):
                            # Debug info
                            print(f"\nDebug {name}:")
                            print(f"- Tipo: {type(tensor)}")
                            print(f"- Shape: {tensor.shape}")
                            print(f"- Device: {tensor.device}")
                            print(f"- Numel: {tensor.numel()}")

                            # Se è un tensore multi-elemento, prendi la media
                            if tensor.numel() > 1:
                                mean_val = float(tensor.mean().detach().cpu())
                                print(f"- Media calcolata: {mean_val}")
                                return mean_val
                            # Se è un tensore singolo, convertilo direttamente
                            single_val = float(tensor.detach().cpu())
                            print(f"- Valore singolo: {single_val}")
                            return single_val
                        # Se è già un numero, convertilo in float
                        float_val = float(tensor)
                        print(f"\nDebug {name} (non tensor):")
                        print(f"- Tipo: {type(tensor)}")
                        print(f"- Valore: {float_val}")
                        return float_val
                    except Exception as e:
                        print(f"\nErrore in safe_tensor_to_float per {name}: {str(e)}")
                        return 0.0

                # Calcola le metriche correnti con gestione sicura
                current_loss = safe_tensor_to_float(trainer.tloss)
                current_lr = safe_tensor_to_float(trainer.optimizer.param_groups[0]['lr'])

                # Stampa sempre il progresso corrente
                progress = f"\rBatch {self.batch_counter} - Epoch {trainer.epoch}/{trainer.epochs}"
                loss_info = f"Loss: {current_loss:.4f}"

                if hasattr(trainer, 'loss_items'):
                    # Gestisci i tensori delle loss individuali in modo sicuro
                    box_loss = safe_tensor_to_float(trainer.loss_items[0])
                    cls_loss = safe_tensor_to_float(trainer.loss_items[1])
                    dfl_loss = safe_tensor_to_float(trainer.loss_items[2])

                    loss_info += f" (Box: {box_loss:.4f}, Cls: {cls_loss:.4f}, Dfl: {dfl_loss:.4f})"

                # Info GPU sempre visibile
                gpu_info = ""
                if torch.cuda.is_available():
                    gpu_mem = torch.cuda.memory_allocated(0)/1024**2
                    gpu_mem_max = torch.cuda.max_memory_allocated(0)/1024**2
                    gpu_info = f" - GPU: {gpu_mem:.0f}MB/{gpu_mem_max:.0f}MB"

                # Stampa sempre l'aggiornamento
                print(f"{progress} - {loss_info}{gpu_info}", end="")

                # Accumula le metriche per wandb
                metrics = {
                    'train/batch': self.batch_counter,
                    'train/epoch': trainer.epoch,
                    'train/loss': current_loss,
                    'train/lr': current_lr
                }

                if hasattr(trainer, 'loss_items'):
                    metrics.update({
                        'train/box_loss': box_loss,
                        'train/cls_loss': cls_loss,
                        'train/dfl_loss': dfl_loss
                    })

                if torch.cuda.is_available():
                    metrics.update({
                        'system/gpu_memory': gpu_mem,
                        'system/gpu_memory_max': gpu_mem_max
                    })

                # Log diretto su wandb per ogni batch
                wandb.log(metrics, step=self.batch_counter)

                # Vai a capo ogni 10 batch per leggibilità
                if self.batch_counter % 10 == 0:
                    print("")  # Nuova riga

                # Stampa un riepilogo ogni 100 batch
                if self.batch_counter % 100 == 0:
                    print(f"\nBatch {self.batch_counter} completato - Loss media: {current_loss:.4f}")

        except Exception as e:
            print(f"\nErrore nel logging batch: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_train_epoch_end(self, trainer):
        try:
            metrics = {
                'train/epoch': trainer.epoch,
                'train/lr': float(trainer.optimizer.param_groups[0]['lr'])
            }
            wandb.log(metrics)
            print(f"\nEpoch {trainer.epoch} completata")

            # Salva il modello ogni 10 epoche
            if trainer.epoch % 10 == 0:
                save_dir = os.path.join('runs/detect', wandb.run.name if wandb.run else 'train', 'weights')
                os.makedirs(save_dir, exist_ok=True)
                checkpoint_path = os.path.join(save_dir, f'epoch_{trainer.epoch}.pt')
                trainer.model.save(checkpoint_path)
                print(f"Checkpoint salvato: {checkpoint_path}")

                # Log del modello su wandb
                if wandb.run is not None:
                    artifact = wandb.Artifact(
                        name=f"model-epoch-{trainer.epoch}", 
                        type="model",
                        description=f"Model checkpoint at epoch {trainer.epoch}"
                    )
                    artifact.add_file(checkpoint_path)
                    wandb.log_artifact(artifact)
                    print(f"Modello epoch {trainer.epoch} loggato su wandb")

        except Exception as e:
            print(f"\nErrore nel logging epoch: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_val_end(self, validator):
        try:
            results = validator.results
            metrics = {
                'val/mAP50': float(results.results_dict['metrics/mAP50(B)']),
                'val/mAP50-95': float(results.results_dict['metrics/mAP50-95(B)']),
                'val/precision': float(results.results_dict['metrics/precision(B)']),
                'val/recall': float(results.results_dict['metrics/recall(B)']),
                'val/box_loss': float(results.results_dict['val/box_loss']),
                'val/cls_loss': float(results.results_dict['val/cls_loss']),
                'val/dfl_loss': float(results.results_dict['val/dfl_loss'])
            }
            total_loss = metrics['val/box_loss'] + metrics['val/cls_loss'] + metrics['val/dfl_loss']
            wandb.log(metrics)
            print(f"Validazione - mAP50: {metrics['val/mAP50']:.4f} | "
                  f"Precision: {metrics['val/precision']:.4f} | "
                  f"Loss: {total_loss:.4f}")
        except Exception as e:
            print(f"Errore logging validazione: {str(e)}")

    def train(self, epochs=100, batch_size=8, img_size=640, resume=True):
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.set_per_process_memory_fraction(0.8)

            model = YOLO('yolov8n.pt')

            data_yaml_path = os.path.join(self.dataset_dir, 'data.yaml')
            if not os.path.exists(data_yaml_path):
                raise FileNotFoundError(f"File data.yaml non trovato in: {data_yaml_path}")

            print(f"Utilizzo file di configurazione: {data_yaml_path}")

            # Solo parametri essenziali e supportati
            train_args = {
                'data': data_yaml_path,
                'epochs': epochs,
                'imgsz': img_size,
                'batch': 2,
                'device': 0 if torch.cuda.is_available() else 'cpu',
                'workers': 0,
                'project': self.project_name,
                'name': wandb.run.name if wandb.run else 'local_run',
                'save': True,
                'lr0': 0.01,
                'lrf': 0.01
            }

            # Registra i callbacks
            model.add_callback('on_train_batch_end', self.on_train_batch_end)
            model.add_callback('on_train_epoch_end', self.on_train_epoch_end)
            model.add_callback('on_val_end', self.on_val_end)

            # Avvia il training
            results = model.train(**train_args)
            return results

        except Exception as e:
            print(f"\nErrore durante il training: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()

def main():
    trainer = ModelTrainer(project_name="RoadDamageDetection")

    try:
        # Inizializza wandb una sola volta all'inizio
        print("Inizializzazione wandb...")
        trainer.init_wandb()

        print("Preparazione dataset...")
        if not trainer.prepare_dataset():
            print("Errore nella preparazione del dataset")
            return

        print("\nAvvio del training...")
        results = trainer.train(
            epochs=100,
            batch_size=8,
            img_size=640,
            resume=True
        )

        print("Addestramento completato con successo!")

    except Exception as e:
        print(f"Errore durante l'esecuzione: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Chiudi wandb solo alla fine di tutto
        if wandb.run is not None:
            wandb.finish()

# Aggiungi questo codice all'inizio di train_model.py
def clean_cache():
    cache_dir = os.path.join('dataset', 'labels', '.cache')
    if os.path.exists(cache_dir):
        print(f"Rimozione cache: {cache_dir}")
        os.remove(cache_dir)

# Chiamalo prima del training
if __name__ == "__main__":
    clean_cache()  # Aggiungi questa riga
    main()