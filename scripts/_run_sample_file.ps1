$out = "C:\Users\HP\Downloads\the-innovaitors-decider-hackathon-kit\the-innovaitors-decider-hackathon-kit\scripts\_run_output.txt"
& "C:\Users\HP\Downloads\the-innovaitors-decider-hackathon-kit\the-innovaitors-decider-hackathon-kit\.venv\Scripts\python.exe" `
  "C:\Users\HP\Downloads\the-innovaitors-decider-hackathon-kit\the-innovaitors-decider-hackathon-kit\scripts\_run_sample.py" `
  2>&1 | Tee-Object -FilePath $out
