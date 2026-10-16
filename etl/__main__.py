"""Allow running pipeline as module: python -m etl.pipeline"""
from etl.pipeline import main
import sys

if __name__ == "__main__":
    sys.exit(main())
