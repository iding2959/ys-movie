### Comfy UI 指定GUP执行

`CUDA_DEVICE_ORDER=PCI_BUS_ID CUDA_VISIBLE_DEVICES=3 python main.py --listen 0.0.0.0 --port 8188 --enable-cors-header --max-upload-size 1073741824`



### basicSR 安装

`pip install --no-cache-dir -U "git+https://github.com/XPixelGroup/BasicSR.git" `


### SageAttention 安装

git clone https://github.com/thu-ml/SageAttention.git
cd SageAttention 
export EXT_PARALLEL=4 NVCC_APPEND_FLAGS="--threads 8" MAX_JOBS=32 # Optional
python setup.py install