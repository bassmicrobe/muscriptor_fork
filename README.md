# MuScriptor

**Kyutai と Mirelo が開発した、マルチ楽器の音楽書き起こしモデルです。**

## 概要

<p align="center">
  <img src="web/logo_muscriptor_final.png" alt="MuScriptor logo" width="300">
</p>

MuScriptor は [Kyutai](https://kyutai.org) と [Mirelo](https://www.mirelo.ai) が開発したマルチ楽器の音楽書き起こしモデルです。クラシックからヘビーメタルまで約 17 万曲の大規模データセットで学習した、初の音楽書き起こしモデルです。アーキテクチャは Transformer デコーダのみです。

[オンラインデモ](https://muscriptor.kyutai.org) | [論文](https://arxiv.org/abs/2607.08168v1) | [HuggingFace](https://huggingface.co/MuScriptor)

3 つのバリアントが [MuScriptor](https://huggingface.co/MuScriptor) 組織配下に公開されています。`load_model()`、CLI の `--model`、`serve --model` ではサイズ名を渡すだけで、重みがダウンロードされローカルにキャッシュされます。

| バリアント | パラメータ数 | レイヤ | Dim | HuggingFace |
|---|---|---|---|---|
| `small` | 103M | 14 | 768 | [muscriptor-small](https://huggingface.co/MuScriptor/muscriptor-small) |
| `medium`（既定） | 307M | 24 | 1024 | [muscriptor-medium](https://huggingface.co/MuScriptor/muscriptor-medium) |
| `large` | 1.4B | 48 | 1536 | [muscriptor-large](https://huggingface.co/MuScriptor/muscriptor-large) |

CPU のみなら `small`、速度と精度のバランスは `medium`、精度最優先（GPU 推奨）は `large` です。

## 技術スタック

- **Python** 3.10 以上（このリポジトリの `.python-version` は 3.13。Intel Mac は 3.10–3.12）
- **パッケージ管理**: uv、[Typer](https://typer.tiangolo.com/) CLI
- **モデル / 推論**: PyTorch、safetensors、Hugging Face Hub、einops、soundfile、mido
- **サーバー**: FastAPI、Uvicorn（`POST /transcribe` は SSE）
- **フロントエンド**（`web/`）: React、TypeScript、Vite、Tailwind CSS、pnpm 10.20.0、Node.js 26.12.1、[SpessaSynth](https://github.com/spessasus/spessasynth_lib)
- **その他**: Docker（`Dockerfile`）、auralize 用 fluidsynth、pytest、pre-commit（Ruff / uv-lock）

## セットアップ

### HuggingFace ログイン（必須）

モデル重みは [HuggingFace](https://huggingface.co/MuScriptor) にあり、CC BY-NC 4.0 のゲート付きです。初回の `uvx muscriptor` を含むダウンロードには、無料の HuggingFace アカウントが必要です。

1. モデルページでライセンスに同意する（例: [muscriptor-medium](https://huggingface.co/MuScriptor/muscriptor-medium)）。アクセスは自動で付与されます。
2. マシンで認証する:

```bash
uvx hf auth login
```

または [トークン](https://huggingface.co/settings/tokens) を設定する:

```bash
export HF_TOKEN=hf_...
```

重みは初回利用時にダウンロードされ、ローカルにキャッシュされます。

### インストール

uv（推奨）:

```bash
uv add muscriptor
```

pip:

```bash
pip install muscriptor
```

> **Intel Mac:** PyTorch は torch 2.2.2 以降 Intel Mac（x86_64）向けホイールを出していません。このバージョンは Python ≤ 3.12 です。`uvx` では Python 3.12 を指定してください。
>
> ```bash
> uvx --python 3.12 muscriptor serve
> ```
>
> pip / uv で入れる場合も Python 3.10–3.12 を使います。

### Web UI のビルド（ソースから動かす場合）

```bash
uv sync
cd web && pnpm install && pnpm run build && cd ..
```

`pnpm run build` は一度必要です。出力先は `muscriptor/web_dist/` で、存在すれば FastAPI が自動マウントします。PyPI の wheel にも同梱されるため、`uvx muscriptor serve` はチェックアウトなしで動きます。

開発時の Node.js は 26.12.1、pnpm は 10.20.0 です（[docs/frontend-nodejs-runtime.md](docs/frontend-nodejs-runtime.md)）。

サウンドフォントは同梱しません。サーバーは初回利用時に [MuScriptor/assets](https://huggingface.co/MuScriptor/assets) から `MuseScore_General.sf2`（215 MB、`/auralize` 用）と `MuseScore_General.sf3`（38 MB、UI 再生用）を取得し、ローカルにキャッシュします（`muscriptor/soundfonts.py`）。

## 使い方

チェックアウトなしで試す場合:

```bash
uvx muscriptor serve
```

CLI:

```bash
uvx muscriptor transcribe
```

### Python API

```python
from pathlib import Path
from muscriptor import TranscriptionModel

# 既定の "medium" を HuggingFace から取得（~/.cache/muscriptor/ にキャッシュ）。
# "small" / "large"、ローカルの safetensors、hf:// や http(s):// も可。
model = TranscriptionModel.load_model()

# イベントをストリームする。楽器は任意指定。名前は `muscriptor list-instruments`。
for event in model.transcribe("audio.wav", instruments=["acoustic_piano", "drums"]):
    print(event)

# MIDI バイト列として取得
midi_bytes = model.transcribe_to_midi("audio.wav")
Path("out.mid").write_bytes(midi_bytes)
```

`transcribe()` は `NoteStartEvent` / `NoteEndEvent` / `ProgressEvent` のジェネレータです。各 `NoteStartEvent` には同じ `index` の `NoteEndEvent` が後続します。ドラムは開始直後にごく短い長さの終了イベントが続きます。ベロシティ（音量）は復元しません。オンセット / オフセット、ピッチ、楽器のみです。

主な引数:

- `audio`: ファイルパス、または `(tensor, sample_rate)`（形状 `[T]` または `[1, T]`）
- `instruments`: 楽器グループ名のリスト（正式名。一覧は `muscriptor list-instruments` または `GET /instruments`）
- `batch_size`: 5 秒チャンクのバッチ。`None` なら CPU で 1、GPU で 4。ストリーミング遅延を抑えるなら `1`
- `use_sampling` / `temperature` / `beam_size`: サンプリングまたはビームサーチ（既定の `beam_size=1` は greedy）
- `cfg_coef`: Classifier-free guidance。公開モデルは post-RL のため `1` のまま
- `no_eos_is_ok`: 生成予算内に EOS が出ないチャンクを警告にする（`True` が既定）

### CLI

```bash
# MIDI へ書き起こし（既定は入力と同じ場所の <audio_file>.mid）
muscriptor transcribe audio.wav -o out.mid

# モデル: small / medium / large（既定: medium）、ローカル safetensors、hf:// / http(s)://
muscriptor transcribe audio.wav --model large

# 想定楽器（カンマ区切り。正式名は `muscriptor list-instruments`）。
# 大文字小文字は無視。曖昧でなければ省略可: 'timp,dist' = timpani + distorted electric guitar
muscriptor transcribe audio.wav --instruments acoustic_piano,drums

# イベント列: json（配列）または jsonl（1 行 1 イベント、-o - は stdout）
muscriptor transcribe audio.wav --format jsonl -o -

# 温度サンプリング、またはビームサーチ
muscriptor transcribe audio.wav --sampling -t 0.8
muscriptor transcribe audio.wav --beam-size 4

# ステレオの確認ミックス（L=元音源、R=合成 MIDI。PATH 上に fluidsynth が必要）
muscriptor transcribe audio.wav -o out.mid --auralize check.wav
```

全オプションは `muscriptor transcribe --help` を参照してください。

### Web UI

`web/` にブラウザクライアントがあります。FastAPI は UI と、`NoteStart` / `NoteEnd` を Server-Sent Events で返す `POST /transcribe` を提供します。WAV のほか、soundfile / libsndfile が読める形式（mp3、flac、ogg、m4a など）をドラッグ & ドロップできます。イベント到着中にピアノロールを描画し、十分なノートが揃うと自動再生し、元 WAV と合成 MIDI をクロスフェードします。

```bash
uv run muscriptor serve \
    --model medium \
    --device cuda \
    --host 0.0.0.0 \
    --port 8222
```

`--model` はサイズ名（`small` / `medium` / `large`）、ローカル safetensors、`hf://` / `http(s)://` を受け付けます。省略時は `medium`。重みは `~/.cache/muscriptor/` にキャッシュされます。

<http://127.0.0.1:8222/>（またはホストの LAN アドレス）を開き、WAV をドロップします。

- CPU のみなら `--device cuda` を外す
- `--host 0.0.0.0` で LAN 公開。既定の `127.0.0.1` はローカルのみ
- 再生はブラウザ内の SoundFont シンセ（[SpessaSynth](https://github.com/spessasus/spessasynth_lib)）で、`MuseScore_General.sf3` を使う。`/auralize` と同じサウンドフォントをアプリが `/soundfonts/` から配信する（サーバー側キャッシュ、第三者 CDN なし）

## 構成

```
.
├── muscriptor/       # Python パッケージ（モデル・CLI・FastAPI）
│   ├── models/
│   ├── modules/
│   ├── tokenizer/
│   └── utils/
├── web/              # Web UI（React / Vite）。ビルド先は muscriptor/web_dist/
├── tests/            # pytest
├── scripts/          # TLS 検証などの補助スクリプト
├── docs/             # 補足ドキュメント
├── Dockerfile
├── swarm.yml         # Docker Swarm デプロイ定義
├── deploy.sh
└── pyproject.toml
```

## ドキュメント

- [フロントエンド Node.js ランタイム](docs/frontend-nodejs-runtime.md)
- [Python TLS セキュリティ更新](docs/python-tls-security.md)

## ライセンス

このリポジトリのコードは [MIT license](LICENSE) です。

[HuggingFace](https://huggingface.co/MuScriptor) のモデル重みは [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/)（非商用）です。

再生 / auralization 用にダウンロードする MuseScore General SoundFont は、それ自体の MIT ライセンスです。

## 引用

```bibtex
@misc{rouard2026muscriptoropenmodelmultiinstrument,
      title={MuScriptor: An Open Model for Multi-Instrument Music Transcription},
      author={Simon Rouard and Michael Krause and Axel Roebel and Carl-Johann Simon-Gabriel and Alexandre Défossez},
      year={2026},
      eprint={2607.08168},
      archivePrefix={arXiv},
      primaryClass={cs.SD},
      url={https://arxiv.org/abs/2607.08168},
}
```
