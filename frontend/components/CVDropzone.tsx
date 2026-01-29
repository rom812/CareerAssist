/**
 * CVDropzone - Drag & Drop PDF Upload Component
 * 
 * Features:
 * - Native HTML5 drag/drop (no external dependencies)
 * - File type validation (PDF only)
 * - File size validation (< 5MB)
 * - Upload progress indicator
 * - Error handling with user-friendly messages
 * 
 * Design Log: /design-log/frontend/011-cv-pdf-upload-parser.md
 */

import { useState, useCallback } from "react";

interface CVDropzoneProps {
    onFileSelect: (file: File) => void;
    uploading: boolean;
    uploadProgress: number;
    disabled?: boolean;
}

const MAX_FILE_SIZE_MB = 5;
const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export function CVDropzone({ 
    onFileSelect, 
    uploading, 
    uploadProgress,
    disabled = false 
}: CVDropzoneProps) {
    const [isDragging, setIsDragging] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);

    const validateFile = (file: File): string | null => {
        // Check file type
        if (file.type !== "application/pdf") {
            return "Only PDF files are supported. Please select a PDF file.";
        }
        
        // Check file size
        if (file.size > MAX_FILE_SIZE_BYTES) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(1);
            return `File is too large (${sizeMB}MB). Maximum size is ${MAX_FILE_SIZE_MB}MB.`;
        }
        
        // Check for empty file
        if (file.size < 100) {
            return "File appears to be empty or corrupted.";
        }
        
        return null;
    };

    const handleFile = useCallback((file: File) => {
        const validationError = validateFile(file);
        if (validationError) {
            setError(validationError);
            setSelectedFile(null);
            return;
        }
        
        setError(null);
        setSelectedFile(file);
        onFileSelect(file);
    }, [onFileSelect]);

    const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
        
        if (disabled || uploading) return;
        
        const file = e.dataTransfer.files[0];
        if (file) {
            handleFile(file);
        }
    }, [disabled, uploading, handleFile]);

    const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        if (!disabled && !uploading) {
            setIsDragging(true);
        }
    }, [disabled, uploading]);

    const handleDragLeave = useCallback((e: React.DragEvent<HTMLDivElement>) => {
        e.preventDefault();
        e.stopPropagation();
        setIsDragging(false);
    }, []);

    const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            handleFile(file);
        }
        // Reset input so same file can be selected again
        e.target.value = "";
    }, [handleFile]);

    const handleRemoveFile = useCallback((e: React.MouseEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setSelectedFile(null);
        setError(null);
    }, []);

    const formatFileSize = (bytes: number): string => {
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    const isDisabled = disabled || uploading;

    return (
        <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`
                relative border-2 border-dashed rounded-lg p-8 text-center transition-all duration-200
                ${isDisabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}
                ${isDragging 
                    ? "border-primary bg-primary/5 scale-[1.02]" 
                    : error 
                        ? "border-red-300 bg-red-50" 
                        : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"
                }
            `}
        >
            <input
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileInput}
                className="hidden"
                id="cv-file-input"
                disabled={isDisabled}
            />
            
            {uploading ? (
                /* Upload Progress State */
                <div className="py-4">
                    <div className="w-16 h-16 mx-auto mb-4 relative">
                        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                            <circle
                                cx="18"
                                cy="18"
                                r="16"
                                fill="none"
                                stroke="#e5e7eb"
                                strokeWidth="3"
                            />
                            <circle
                                cx="18"
                                cy="18"
                                r="16"
                                fill="none"
                                stroke="#3b82f6"
                                strokeWidth="3"
                                strokeDasharray={`${uploadProgress}, 100`}
                                strokeLinecap="round"
                                className="transition-all duration-300"
                            />
                        </svg>
                        <span className="absolute inset-0 flex items-center justify-center text-sm font-medium text-primary">
                            {uploadProgress}%
                        </span>
                    </div>
                    <p className="text-gray-600 font-medium">Uploading your CV...</p>
                    <p className="text-sm text-gray-500 mt-1">
                        {selectedFile?.name}
                    </p>
                </div>
            ) : selectedFile && !error ? (
                /* File Selected State */
                <div className="py-4">
                    <div className="text-5xl mb-4">📄</div>
                    <p className="font-medium text-dark text-lg">{selectedFile.name}</p>
                    <p className="text-sm text-gray-500 mt-1">
                        {formatFileSize(selectedFile.size)}
                    </p>
                    <button
                        onClick={handleRemoveFile}
                        className="mt-3 px-4 py-1.5 text-sm text-red-600 hover:text-red-700 hover:bg-red-50 rounded-lg transition-colors"
                    >
                        Remove file
                    </button>
                </div>
            ) : (
                /* Default/Empty State */
                <label 
                    htmlFor="cv-file-input" 
                    className={`block py-4 ${isDisabled ? "cursor-not-allowed" : "cursor-pointer"}`}
                >
                    <div className="text-5xl mb-4">
                        {isDragging ? "📥" : "📤"}
                    </div>
                    <p className="text-gray-700 mb-2 text-lg">
                        {isDragging ? (
                            <span className="text-primary font-medium">Drop your CV here</span>
                        ) : (
                            <>
                                Drag & drop your CV here, or{" "}
                                <span className="text-primary font-medium hover:underline">
                                    browse
                                </span>
                            </>
                        )}
                    </p>
                    <p className="text-sm text-gray-400">
                        PDF files only, maximum {MAX_FILE_SIZE_MB}MB
                    </p>
                </label>
            )}
            
            {/* Error Message */}
            {error && (
                <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                    <p className="text-sm text-red-600 flex items-center gap-2">
                        <span>⚠️</span>
                        {error}
                    </p>
                </div>
            )}
            
            {/* Privacy Notice */}
            <div className="mt-6 pt-4 border-t border-gray-100">
                <p className="text-xs text-gray-400 flex items-center justify-center gap-2">
                    <span>🔒</span>
                    <span>Your file is processed securely and never shared</span>
                </p>
            </div>
        </div>
    );
}
