#!/usr/bin/env python3
# 6_generar_evidencia.py  (robusto con resolución de rutas + confusión)
import argparse, json, sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

SCRIPT_DIR = Path(__file__).resolve().parent

def resolve_here_first(p: Path) -> Path:
    if p.is_absolute() and p.exists():
        return p
    if p.exists():
        return p
    alt = SCRIPT_DIR / p.name
    if alt.exists():
        return alt
    return p

def _safe_load(path, loader):
    p = resolve_here_first(Path(path))
    if not p.exists():
        print(f"[WARN] No encontrado: {p}")
        return None
    try:
        v = loader(p)
        print(f"[OK] Usando: {p}")
        return v
    except Exception as e:
        print(f"[WARN] No pude cargar {p}: {e}")
        return None

def _savefig(name):
    name = resolve_here_first(Path(name))
    plt.tight_layout()
    plt.savefig(name, dpi=200)
    print(f"[OK] Figura: {name}")

# ──────────────────────────────────────────────────────────────────────────────
# A) Dataset & features (+ verificación de partición si hay groups)
# ──────────────────────────────────────────────────────────────────────────────
def gen_dataset_figures(y_train="y_train.npy", y_test="y_test.npy",
                        feat_path="X_ransomware_features.npy",
                        names_path="ransomware_feature_names.txt",
                        groups_path="groups.npy",
                        train_idx_path="train_idx.npy",
                        test_idx_path="test_idx.npy"):
    print("\n[DATASET] Generando figuras de dataset...")
    ytr = _safe_load(y_train, lambda p: np.argmax(np.load(p), 1))
    yte = _safe_load(y_test,  lambda p: np.argmax(np.load(p), 1))

    if ytr is not None:
        plt.figure()
        vals = [np.sum(ytr == 0), np.sum(ytr == 1)]
        plt.bar(['Train-Benign','Train-Malw'], vals)
        plt.title('Class dist - Train')
        _savefig('fig_dist_train.png')

    if yte is not None:
        plt.figure()
        vals = [np.sum(yte == 0), np.sum(yte == 1)]
        plt.bar(['Test-Benign','Test-Malw'], vals)
        plt.title('Class dist - Test')
        _savefig('fig_dist_test.png')

    # Verificación de partición por PCAP (si existen archivos)
    groups   = _safe_load(groups_path, lambda p: np.load(p))
    train_id = _safe_load(train_idx_path, lambda p: np.load(p))
    test_id  = _safe_load(test_idx_path,  lambda p: np.load(p))
    if groups is not None and train_id is not None and test_id is not None:
        train_pcaps = groups[train_id]
        test_pcaps  = groups[test_id]
        uniq_train  = np.unique(train_pcaps)
        uniq_test   = np.unique(test_pcaps)
        inter       = np.intersect1d(uniq_train, uniq_test)

        print("\n[DATASET] Verificación de partición por PCAP:")
        print(f"  PCAPs únicos en train: {len(uniq_train)}")
        print(f"  PCAPs únicos en test:  {len(uniq_test)}")
        print(f"  Overlap train/test:    {len(inter)}")
        if len(inter) == 0:
            print("  ✅ Sin solapamiento de PCAPs (sin data leakage).")
        else:
            print("  ❌ Hay solapamiento de PCAPs (posible data leakage).")

        lines = []
        if ytr is not None and yte is not None:
            tr = np.bincount(ytr, minlength=2).tolist()
            te = np.bincount(yte, minlength=2).tolist()
            lines += [
                "Distribución de clases:",
                f"  Train -> benign: {tr[0]} | malware: {tr[1]}",
                f"  Test  -> benign: {te[0]} | malware: {te[1]}",
                ""
            ]
        lines += [
            "Partición por PCAP:",
            f"  PCAPs únicos en train: {len(uniq_train)}",
            f"  PCAPs únicos en test:  {len(uniq_test)}",
            f"  Overlap train/test:    {len(inter)}",
            "  OK sin leakage" if len(inter) == 0 else "  ATENCIÓN: hay leakage",
            ""
        ]
        rpt = resolve_here_first(Path("dataset_partition_report.txt"))
        rpt.write_text("\n".join(lines), encoding="utf-8")
        print(f"[OK] Reporte: {rpt}")

    feat  = _safe_load(feat_path,  lambda p: np.load(p))
    names = _safe_load(names_path, lambda p: [l.strip() for l in open(p,'r',encoding='utf-8')]) if feat is not None else None
    if feat is not None and names is not None and 'entropy_mean' in names:
        ei = names.index('entropy_mean')
        plt.figure()
        plt.hist(feat[:, ei], bins=40)
        plt.title('Entropy (mean)')
        _savefig('fig_entropy_hist.png')
    else:
        print("[INFO] Sin histograma de entropía (no hay features o nombres).")

# ──────────────────────────────────────────────────────────────────────────────
# B) Curvas de entrenamiento
# ──────────────────────────────────────────────────────────────────────────────
def gen_training_curves(history_json="history.json"):
    print("\n[TRAINING] Curvas de entrenamiento...")
    h = _safe_load(history_json, lambda p: json.load(open(p, 'r', encoding='utf-8')))
    if h is None:
        print("[INFO] No hay history.json, salteando curvas.")
        return
    for k in ['loss', 'accuracy']:
        if k in h and ('val_'+k) in h:
            plt.figure()
            plt.plot(h[k], label=k)
            plt.plot(h['val_'+k], label='val_'+k)
            plt.legend()
            plt.title(k)
            plt.xlabel('epoch')
            plt.ylabel(k)
            _savefig(f'fig_{k}.png')
        else:
            print(f"[INFO] No encontré series para {k} y val_{k} en history.json.")

# ──────────────────────────────────────────────────────────────────────────────
# C) Matriz de confusión desde predicciones guardadas (paso 4)
# ──────────────────────────────────────────────────────────────────────────────
def gen_confusion_matrix(tag="base",
                         y_true_path=None,
                         y_pred_path=None):
    from sklearn.metrics import confusion_matrix
    print("\n[CONFUSION] Generando matriz de confusión...")

    # por defecto usa los nombres que guarda el paso 4 con ese tag
    if y_true_path is None:
        y_true_path = f"y_true_{tag}.npy"
    if y_pred_path is None:
        y_pred_path = f"y_pred_{tag}.npy"

    y_true = _safe_load(y_true_path, lambda p: np.load(p))
    y_pred = _safe_load(y_pred_path, lambda p: np.load(p))
    if y_true is None or y_pred is None:
        print("[INFO] No hay y_true/y_pred para confusión.")
        return

    class_names = ["Benigno", "Ransomware/Malware"]
    cm = confusion_matrix(y_true, y_pred)                   # absolutos
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)  # normalizada por fila

    # Absoluta
    plt.figure()
    import seaborn as sns
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names)
    plt.xlabel('Predicho'); plt.ylabel('Real')
    plt.title(f'Matriz de confusión ({tag})')
    _savefig(f'fig_confusion_matrix_{tag}.png')

    # Normalizada
    plt.figure()
    sns.heatmap(cm_norm, annot=True, fmt='.3f', cmap='Greens',
                xticklabels=class_names, yticklabels=class_names)
    plt.xlabel('Predicho'); plt.ylabel('Real')
    plt.title(f'Matriz de confusión normalizada ({tag})')
    _savefig(f'fig_confusion_matrix_norm_{tag}.png')

# ──────────────────────────────────────────────────────────────────────────────
# D) ASR sweep (ε) + gráfico
# ──────────────────────────────────────────────────────────────────────────────
def run_asr_sweep(model_path="convlstm_model.keras",
                  y_path="y_test.npy",
                  eps_list="0.00,0.01,0.02,0.03,0.05",
                  adv_pattern="X_adv_test_eps{eps}.npy",
                  out_csv="asr_vs_eps.csv",
                  plot=True):
    print("\n[ASR] Sweep de ε...")
    try:
        from tensorflow.keras.models import load_model
    except Exception as e:
        print(f"[ERROR] TensorFlow requerido para asr_sweep: {e}")
        return

    candidates = [Path(model_path), SCRIPT_DIR / "convlstm_model_best.keras", SCRIPT_DIR / "convlstm_model.keras"]
    model = None; tried = []
    for c in candidates:
        rc = resolve_here_first(c); tried.append(str(rc))
        if rc.exists():
            model = load_model(rc); print(f"[OK] Modelo para ASR: {rc}"); break
    if model is None:
        print(f"[INFO] Sin modelo para ASR. Probé: {', '.join(tried)}"); return

    y_test = _safe_load(y_path, lambda p: np.load(p))
    if y_test is None: print("[INFO] Sin y_test, no se puede hacer ASR sweep."); return
    y_true = np.argmax(y_test, axis=1)

    rows = []
    for eps_s in eps_list.split(','):
        eps = float(eps_s)
        x_path = adv_pattern.format(eps=f"{eps:.2f}")
        X_adv = _safe_load(x_path, lambda p: np.load(p))
        if X_adv is None: print(f"[WARN] Falta {x_path}; continuo."); continue
        y_pred = model.predict(X_adv, verbose=0).argmax(1)
        asr = float(np.mean(y_pred != y_true))
        rows.append((eps, asr))
        print(f"  ε={eps:.2f} → ASR={asr:.4f}")

    if not rows:
        print("[INFO] No hay filas para ASR (faltan X_adv*).")
        return

    import csv
    out_csv = resolve_here_first(Path(out_csv))
    with open(out_csv, 'w', newline='') as f:
        w = csv.writer(f); w.writerow(['epsilon', 'asr'])
        for r in rows: w.writerow(r)
    print(f"[OK] Guardado {out_csv}")

    if plot:
        eps_vals = [r[0] for r in rows]; asr_vals = [r[1] for r in rows]
        plt.figure(); plt.plot(eps_vals, asr_vals, marker='o')
        plt.xlabel('ε'); plt.ylabel('ASR'); plt.title('ASR vs ε')
        _savefig('fig_asr_vs_eps.png')

# ──────────────────────────────────────────────────────────────────────────────
# E) Comparativa de robustez (F1 Malware) a partir de JSONs
# ──────────────────────────────────────────────────────────────────────────────
def gen_robustness_comparison(base_json="evaluation_results_base.json",
                              attack_json="evaluation_results_attack.json",
                              adv_json="evaluation_results_advtrain.json"):
    print("\n[ROBUSTNESS] Comparativa Base vs Attack vs AdvTrain...")
    def f1_from(path):
        d = _safe_load(path, lambda p: json.load(open(p, 'r', encoding='utf-8')))
        if d is None: return None
        try: return d['ransomware_specific_metrics']['f1_score']
        except Exception: return None

    f1_base = f1_from(base_json); f1_attk = f1_from(attack_json); f1_adv = f1_from(adv_json)
    labels, values = [], []
    if f1_base is not None: labels.append('Base');     values.append(f1_base)
    if f1_attk is not None: labels.append('Attack');   values.append(f1_attk)
    if f1_adv  is not None: labels.append('AdvTrain'); values.append(f1_adv)
    if not values: print("[INFO] No pude leer F1s de los JSONs de evaluación."); return

    plt.figure(figsize=(5, 5))
    bars = plt.bar(labels, values, color=["#1976D2"])
    plt.ylabel('F1 (Ransomware)'); plt.title('Robustness Comparison')
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x()+bar.get_width()/2, yval+0.02, f"{yval:.2f}", ha='center', va='bottom', fontsize=12, fontweight='bold')
    plt.ylim(0, 1.0); plt.grid(axis='y', linestyle='--', alpha=0.5)
    _savefig('fig_robustez_f1.png')

# ──────────────────────────────────────────────────────────────────────────────
# Main / CLI
# ──────────────────────────────────────────────────────────────────────────────
def parse_args():
    ap = argparse.ArgumentParser(description="Generación unificada de evidencia/figuras")
    ap.add_argument('--dataset', action='store_true', help='Generar figuras de dataset (+ partición si hay groups)')
    ap.add_argument('--training', action='store_true', help='Generar curvas de entrenamiento')
    ap.add_argument('--confmat', action='store_true', help='Generar matriz de confusión desde y_true/y_pred guardados')
    ap.add_argument('--asr_sweep', action='store_true', help='Correr sweep ε para ASR y graficar')
    ap.add_argument('--robustness', action='store_true', help='Generar comparativa Base/Attack/AdvTrain')
    ap.add_argument('--all', action='store_true', help='Hacer todo lo posible')

    # dataset
    ap.add_argument('--y_train', default='y_train.npy')
    ap.add_argument('--y_test',  default='y_test.npy')
    ap.add_argument('--feat', default='X_ransomware_features.npy')
    ap.add_argument('--feat_names', default='ransomware_feature_names.txt')
    ap.add_argument('--groups', default='groups.npy')
    ap.add_argument('--train_idx', default='train_idx.npy')
    ap.add_argument('--test_idx', default='test_idx.npy')

    # training curves
    ap.add_argument('--history', default='history.json')

    # confmat
    ap.add_argument('--tag', default='base')
    ap.add_argument('--y_true_path', default=None)
    ap.add_argument('--y_pred_path', default=None)

    # ASR
    ap.add_argument('--model', default='convlstm_model.keras')
    ap.add_argument('--y', default='y_test.npy')
    ap.add_argument('--eps_list', default='0.00,0.01,0.02,0.03,0.05')
    ap.add_argument('--adv_pattern', default='X_adv_test_eps{eps}.npy')
    ap.add_argument('--asr_csv', default='asr_vs_eps.csv')

    # robustness
    ap.add_argument('--base_json',   default='evaluation_results_base.json')
    ap.add_argument('--attack_json', default='evaluation_results_attack.json')
    ap.add_argument('--adv_json',    default='evaluation_results_advtrain.json')
    return ap.parse_args()

def main():
    args = parse_args()
    if args.all:
        args.dataset = args.training = args.confmat = args.asr_sweep = args.robustness = True

    if not any([args.dataset, args.training, args.confmat, args.asr_sweep, args.robustness]):
        print("Nada para hacer. Usá --all o flags individuales. Ej: --dataset --training")
        sys.exit(0)

    if args.dataset:
        gen_dataset_figures(args.y_train, args.y_test, args.feat, args.feat_names,
                            args.groups, args.train_idx, args.test_idx)

    if args.training:
        gen_training_curves(args.history)

    if args.confmat:
        gen_confusion_matrix(tag=args.tag, y_true_path=args.y_true_path, y_pred_path=args.y_pred_path)

    if args.asr_sweep:
        run_asr_sweep(args.model, args.y, args.eps_list, args.adv_pattern, args.asr_csv, plot=True)

    if args.robustness:
        gen_robustness_comparison(args.base_json, args.attack_json, args.adv_json)

    print("\n[DONE] Evidencia generada (lo disponible).")

if __name__ == "__main__":
    main()