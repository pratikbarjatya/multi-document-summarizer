import requests
from flask import request, jsonify
from flask_login import current_user, login_required
from flask import Blueprint, request, jsonify
from models import db, Document, Summary

document_bp = Blueprint("documents", __name__)

# Get all documents for the current user
@document_bp.route("/get-all-documents", methods=["GET"])
@login_required
def get_all_documents():
    documents = Document.query.filter_by(user_id=current_user.user_id).all()
    user = current_user
    document_list = []

    for doc in documents:
        document_data = {
            "name": doc.title,
            "dateUploaded": doc.upload_date.strftime("%B %d, %Y"),
            "id": doc.document_id,
            "content": doc.content,
            "user": user.username,
        }
        document_list.append(document_data)

    return jsonify(document_list)


# Delete a document by document_id for the current user
@document_bp.route("/delete-document/<int:document_id>", methods=["DELETE"])
@login_required
def delete_document(document_id):
    document = Document.query.get(document_id)
    if document:
        # Check if the document belongs to the current user
        if document.user_id == current_user.user_id:
            db.session.delete(document)
            db.session.commit()
            return jsonify({"message": f"Document with ID {document_id} deleted successfully"})
        else:
            return jsonify({"error": "You don't have permission to delete this document"}), 403
    else:
        return jsonify({"error": f"Document with ID {document_id} not found"}), 404


# Get content of a document
@document_bp.route('/get-document-content/<int:document_id>')
@login_required
def get_document_content(document_id):
    # Fetch the document based on document_id
    document = Document.query.get(document_id)

    if document:
        # Check if the document belongs to the current user
        if document.user_id == current_user.user_id:
            return document.content  # Assuming the 'content' attribute holds the document content
        else:
            return "Unauthorized - You don't have permission to access this document", 403
    else:
        return "Document not found", 404

# Upload a document for the current user


@document_bp.route("/upload-document", methods=["POST"])
@login_required
def upload_document():
    # Check if files were sent
    if "content0" in request.files:
        document_ids = []

        for i in range(len(request.files)):
            # Get the content for each file and extract text from PDF files
            file = request.files.get(f"content{i}")
            # Default title if not provided
            title = request.form.get(f"title{i}", "Untitled")

            if file.filename.lower().endswith(".pdf"):
                # This is a PDF file, extract text using PyPDF2
                pdf_text = extract_text_from_pdf(file)
                content = pdf_text
            else:
                # For non-PDF files, simply read the content
                content = file.read().decode("utf-8")

            new_document = Document(
                title=title, content=content, user_id=current_user.user_id)
            db.session.add(new_document)
            db.session.commit()
            document_ids.append(new_document.document_id)

        if document_ids:
            return jsonify({"document_ids": document_ids, "message": "Documents uploaded successfully"})
        else:
            return jsonify({"error": "No valid documents uploaded"}), 400
    else:
        return jsonify({"error": "No content provided"}), 400
    

@document_bp.route("/upload-document-link", methods=["POST"])
@login_required
def upload_document_link():
    #data = request.get_json()
    link = request.json.get("link")
    title = request.json.get("title", "Untitled")

    if not link:
        return jsonify({"error": "No document link provided"}), 400

    try:
        response = requests.get(link)
        response.raise_for_status()
        
        content = response.text

        content = sanitize_text(content)
        new_document = Document(title=title, content=content, user_id=current_user.user_id)
        db.session.add(new_document)
        db.session.commit()

        return jsonify({"document_id": new_document.document_id, "message": "Document uploaded successfully"})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to fetch document content from the provided link"}), 400
    
@document_bp.route("/upload-document-news", methods=["POST"])
@login_required
def upload_document_news():
    try:

        title = request.json.get("title")
        content = request.json.get("content")

        new_document = Document(
            title=title, content=content, user_id=current_user.user_id)
        db.session.add(new_document)
        db.session.commit()

        return jsonify({"document_id": new_document.document_id, "message": "Document uploaded successfully"})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": "Failed to fetch document content from the provided link"}), 400


def sanitize_text(text):
    # Remove null characters and other non-printable characters
    sanitized_text = ''.join(char for char in text if char.isprintable())
    return sanitized_text

import PyPDF2
def extract_text_from_pdf(pdf_file):
    pdf_text = ""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
    except PyPDF2.utils.PdfrReadError:
        # Handle invalid or corrupted PDF files
        pdf_text = "Invalid or corrupted PDF file"
    return pdf_text

