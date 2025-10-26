#!/usr/bin/env python3
# 6_visual_dashboard.py  — dashboard 2×3 en una sola figura
import argparse, json
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import confusion_matrix, roc_curve, auc, precision_recall_curve

def load_json(p): 
    with open(p, 'r', encoding='utf-8') as f: return json.load(f)

def main():
    ap = argparse.ArgumentParser(description="Dashboard único de evaluación")
    ap.add_argument("--tag", default="base", help="Sufijo usado en el paso 4 (base/attack/advtrain)")
    ap.add_argument("--indir", default=".", help="Carpeta donde están los artefactos del paso 4")
    ap.add_argument("--out", default="evaluation_dashboard", help="Prefijo de salida (sin extensión)")
    ap.add_argument("--no_emojis", action="store_true", help="Evita emojis en el panel de texto")
    args = ap.parse_args()

    indir = Path(args.indir)
    out_prefix = Path(args.out)

    # Archivos esperados del paso 4
    res_path   = indir / f"evaluation_results_{args.tag}.json"
    proba_path = indir / f"y_pred_proba_{args.tag}.npy"
    ytrue_path = indir / f"y_true_{args.tag}.npy"

    if not res_path.exists():
        raise FileNotFoundError(f"No encontré {res_path}. Corré primero el paso 4 con --tag {args.tag}")
    if not proba_path.exists():
        raise FileNotFoundError(f"No encontré {proba_path}. Corré primero el paso 4 con --tag {args.tag}")
    if not ytrue_path.exists():
        raise FileNotFoundError(f"No encontré {ytrue_path}. Corré primero el paso 4 con --tag {args.tag}")

    results = load_json(res_path)
    y_pred_proba = np.load(proba_path)   # (N,2)
    y_true = np.load(ytrue_path)         # (N,)

    class_names = ["Benigno", "Ransomware"]
    # CM del JSON
    tn = results['confusion_matrix']['true_negatives']
    fp = results['confusion_matrix']['false_positives']
    fn = results['confusion_matrix']['false_negatives']
    tp = results['confusion_matrix']['true_positives']
    cm = np.array([[tn, fp], [fn, tp]], dtype=np.int64)

    # ROC / PR desde y_true + proba
    fpr, tpr, _ = roc_curve(y_true, y_pred_proba[:, 1])
    roc_auc = auc(fpr, tpr)
    prec, rec, _ = precision_recall_curve(y_true, y_pred_proba[:, 1])
    avg_precision = results.get('average_precision', (prec*rec).sum())  # fallback simple

    # Distribución de probabilidades
    benign_probs = y_pred_proba[y_true == 0, 1]
    malw_probs   = y_pred_proba[y_true == 1, 1]

    # Métricas por clase (del JSON)
    cr = results['classification_report']
    ben = cr['Benigno']
    mal = cr['Ransomware/Malware']

    # Figura 2×3
    plt.style.use('seaborn-v0_8')
    sns.set_palette("husl")
    fig = plt.figure(figsize=(20, 12))
    fig.suptitle(f"Dashboard de Evaluación — tag: {args.tag}", fontsize=16, fontweight='bold')

    # 1) CM absoluta
    ax = plt.subplot(2,3,1)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=class_names, yticklabels=class_names, ax=ax,
                cbar_kws={'label':'# muestras'}, linewidths=.5, linecolor='white')
    ax.set_title("Matriz de Confusión (absoluta)")
    ax.set_xlabel("Predicho"); ax.set_ylabel("Real")

    # 2) ROC
    ax = plt.subplot(2,3,2)
    ax.plot(fpr, tpr, lw=2, label=f'AUC={roc_auc:.3f}')
    ax.plot([0,1],[0,1],'--', lw=1)
    ax.set_xlim(0,1); ax.set_ylim(0,1.05)
    ax.set_xlabel('FPR'); ax.set_ylabel('TPR'); ax.set_title("Curva ROC"); ax.legend(loc='lower right')

    # 3) Precision–Recall
    ax = plt.subplot(2,3,3)
    ax.plot(rec, prec, lw=2, label=f'AP={avg_precision:.3f}')
    ax.set_xlim(0,1); ax.set_ylim(0,1.05)
    ax.set_xlabel('Recall'); ax.set_ylabel('Precision'); ax.set_title("Curva Precision–Recall"); ax.legend(loc='lower left')

    # 4) CM normalizada (por fila)
    ax = plt.subplot(2,3,4)
    cm_norm = cm.astype(float) / cm.sum(axis=1, keepdims=True)
    sns.heatmap(cm_norm, annot=True, fmt='.3f', cmap='Greens',
                xticklabels=class_names, yticklabels=class_names, ax=ax,
                cbar_kws={'label':'Proporción'}, linewidths=.5, linecolor='white')
    ax.set_title("Matriz de Confusión (normalizada por fila)")
    ax.set_xlabel("Predicho"); ax.set_ylabel("Real")

    # 5) Distribución de probabilidades
    ax = plt.subplot(2,3,5)
    ax.hist(benign_probs, bins=30, alpha=0.7, label='Benigno')
    ax.hist(malw_probs,   bins=30, alpha=0.7, label='Ransomware')
    ax.axvline(0.5, color='k', linestyle='--', lw=1, label='Umbral 0.5')
    ax.set_xlabel('Prob. clase Ransomware'); ax.set_ylabel('Frecuencia')
    ax.set_title("Distribución de probabilidades"); ax.legend()

    # 6) Métricas por clase (barras)
    ax = plt.subplot(2,3,6)
    labels = ['Benigno', 'Ransomware']
    precs  = [ben['precision'], mal['precision']]
    recs   = [ben['recall'],    mal['recall']]
    f1s    = [ben['f1-score'],  mal['f1-score']]
    x = np.arange(len(labels)); w = 0.25
    ax.bar(x - w, precs, w, label='Precision', alpha=0.85)
    ax.bar(x,      recs,  w, label='Recall',    alpha=0.85)
    ax.bar(x + w,  f1s,   w, label='F1-Score',  alpha=0.85)
    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_ylim(0,1.0); ax.legend(); ax.set_title("Métricas por clase")

    # Texto resumen (opcional: lo podés agregar como caption en la tesis)
    sens = results['confusion_matrix']['sensitivity']
    spec = results['confusion_matrix']['specificity']
    acc  = results['basic_metrics']['accuracy']
    f1m  = results['ransomware_specific_metrics']['f1_score']
    ap   = results['average_precision']

    print("\n— RESUMEN —")
    print(f"Accuracy: {acc:.4f} | F1(Malware): {f1m:.4f} | ROC AUC: {roc_auc:.4f} | AP: {ap:.4f}")
    print(f"Sensitivity: {sens:.4f} | Specificity: {spec:.4f}")
    print(f"TP={tp}  TN={tn}  FP={fp}  FN={fn}  | N={len(y_true)}")

    out_png = out_prefix.with_suffix(".png")
    out_pdf = out_prefix.with_suffix(".pdf")
    fig.tight_layout(rect=[0, 0.02, 1, 0.95])
    fig.savefig(out_png, dpi=300, facecolor='white', bbox_inches='tight')
    fig.savefig(out_pdf,            facecolor='white', bbox_inches='tight')
    print(f"\n✅ Guardado: {out_png}")
    print(f"✅ Guardado: {out_pdf}")

if __name__ == "__main__":
    main()