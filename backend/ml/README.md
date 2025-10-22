# 🤖 SageMaker Denial Prediction Model

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Test locally:**
   ```bash
   python train.py
   ```

3. **Deploy to SageMaker:**
   ```bash
   python deploy_sagemaker.py
   ```

4. **Test endpoint:**
   ```bash
   python test_sagemaker.py
   ```

5. **Cleanup (to stop charges):**
   ```bash
   python cleanup_sagemaker.py
   ```

## Files

- `train.py` - Training script (works locally & on SageMaker)
- `inference.py` - Inference handler for SageMaker endpoint
- `deploy_sagemaker.py` - Deploy model to SageMaker
- `test_sagemaker.py` - Test deployed endpoint
- `cleanup_sagemaker.py` - Delete endpoint to stop charges
- `requirements.txt` - Python dependencies

## Cost

- **Training:** ~$0.025 (one-time, 10 minutes)
- **Endpoint:** ~$0.05/hour (~$36/month if left running)

**Remember to cleanup after hackathon!**

## Documentation

See `SAGEMAKER_DEPLOYMENT.md` in project root for full guide.
