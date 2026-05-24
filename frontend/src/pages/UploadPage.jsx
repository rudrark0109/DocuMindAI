import React, {useState} from 'react';
import {uploadDocument} from '../services/documentApi';

function UploadPage() {
    const [selectedFile, setSelectedFile] = useState(null);
    const [uploadResult, setUploadResult] = useState(null);
    const [errorMessage, setErrorMessage] = useState("");
    const [isUploading, setIsUploading] = useState(false);

    function handleFileChange(event) {
        setSelectedFile(event.target.files[0]);
        setUploadResult(null);
        setErrorMessage("");
    }

    async function handleUpload() {
        if (!selectedFile) {
            setErrorMessage("Please select a file to upload.");
            return;
        }

        try {
            setIsUploading(true);
            setErrorMessage("");

            const result = await uploadDocument(selectedFile);
            setUploadResult(result);
        } catch (error) {
            setErrorMessage("Failed to upload document.");
        } finally {
            setIsUploading(false);
        }
    }
    return (
        <>
        <main>
            <h1>DocuMind AI</h1>
            <h2>Upload Document</h2>

            <input type="file" onChange={handleFileChange} accept=".pdf,.png,.jpg,.jpeg"/>
            <button onClick={handleUpload} disabled={isUploading}>
                {isUploading ? "Uploading..." : "Upload"}
            </button>

            {errorMessage && <p style={{color: "red"}}>{errorMessage}</p>}
            {uploadResult && (
                <div>
                    <h3>Upload Successful</h3>
                    <p>Original File: {uploadResult.original_filename}</p>
                    <p>Saved File: {uploadResult.saved_filename}</p>
                    <p>Path: {uploadResult.file_path}</p>
                    <p>Type: {uploadResult.content_type}</p>
                </div>
            )}
        </main>
        </>
    );
}

export default UploadPage;
