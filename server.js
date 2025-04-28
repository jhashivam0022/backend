const express = require('express');
const multer = require('multer');
const { spawn } = require('child_process');
const path = require('path');
const cors = require('cors');

const app = express();
app.use(cors());

const PORT = process.env.PORT || 5000;
const upload = multer({ dest: 'uploads/' });

app.post('/start-verification', upload.single('file'), (req, res) => {
  const filePath = req.file.path;

  const pythonProcess = spawn('python', ['selenium_script.py', filePath]);

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python output: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    if (code === 0) {
      res.json({ message: 'PAN verification completed successfully.' });
    } else {
      res.status(500).json({ message: 'Python script failed.' });
    }
  });
});

app.listen(PORT, () => {
  console.log(`Server running on http://localhost:${PORT}`);
});
