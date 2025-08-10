"""
Serializers for documents application REST API
"""

from rest_framework import serializers
from .models import Document


class DocumentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for document lists"""
    
    category_name = serializers.CharField(source='category', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'uuid', 'name', 'category_name', 'file_size_mb', 
            'file_type', 'created_at', 'is_active'
        ]
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        if obj.file:
            try:
                size_bytes = obj.file.size
                return round(size_bytes / (1024 * 1024), 2)
            except:
                return 0
        return 0
    
    def get_file_type(self, obj):
        """Get file extension"""
        if obj.name and '.' in obj.name:
            return obj.name.split('.')[-1].lower()
        return 'unknown'


class DocumentSerializer(serializers.ModelSerializer):
    """Detailed serializer for document model"""
    
    category_name = serializers.CharField(source='category', read_only=True)
    file_size_mb = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    text_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'uuid', 'name', 'category_name', 'file', 'file_size_mb', 'file_type',
            'file_hash', 'extracted_text', 'text_preview', 'tags',
            'is_active', 'created_at', 'updated_at', 'download_url'
        ]
        read_only_fields = [
            'uuid', 'file_hash', 'extracted_text', 'created_at', 
            'updated_at', 'file_size_mb', 'file_type', 'download_url', 'text_preview'
        ]
    
    def get_file_size_mb(self, obj):
        """Get file size in MB"""
        if obj.file:
            try:
                size_bytes = obj.file.size
                return round(size_bytes / (1024 * 1024), 2)
            except:
                return 0
        return 0
    
    def get_file_type(self, obj):
        """Get file extension"""
        if obj.name and '.' in obj.name:
            return obj.name.split('.')[-1].lower()
        return 'unknown'
    
    def get_download_url(self, obj):
        """Get document download URL"""
        return f"/api/documents/download/{obj.uuid}/"
    
    def get_text_preview(self, obj):
        """Get preview of extracted text"""
        if obj.extracted_text:
            return obj.extracted_text[:500] + "..." if len(obj.extracted_text) > 500 else obj.extracted_text
        return ""


# CompanyDocument model not implemented yet


class DocumentSearchSerializer(serializers.Serializer):
    """Serializer for document search requests"""
    
    query = serializers.CharField(max_length=500, required=True)
    categories = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    file_types = serializers.ListField(
        child=serializers.CharField(max_length=10),
        required=False,
        allow_empty=True
    )
    
    def validate_query(self, value):
        """Validate search query"""
        if not value.strip():
            raise serializers.ValidationError("Search query cannot be empty")
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Search query must be at least 2 characters")
        return value.strip()
    
    def validate_file_types(self, value):
        """Validate file types"""
        allowed_types = ['pdf', 'doc', 'docx', 'txt', 'md', 'html', 'rtf']
        for file_type in value:
            if file_type.lower() not in allowed_types:
                raise serializers.ValidationError(f"File type '{file_type}' is not supported")
        return [ft.lower() for ft in value]


class DocumentUploadSerializer(serializers.ModelSerializer):
    """Serializer for document upload"""
    
    category_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Document
        fields = ['name', 'file', 'category_id', 'metadata', 'is_active']
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("File is required")
        
        # Check file size (max 10MB)
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("File size cannot exceed 10MB")
        
        # Check file type
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md', '.html', '.rtf']
        if not any(value.name.lower().endswith(ext) for ext in allowed_extensions):
            raise serializers.ValidationError(
                f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
            )
        
        return value
    
    def validate_category_id(self, value):
        """Validate category name"""
        # Since category is just a CharField, any string is valid
        return value
    
    def create(self, validated_data):
        """Create document with category"""
        category_name = validated_data.pop('category_id', None)  # Reuse the field as category name
        
        document = Document.objects.create(**validated_data)
        
        if category_name:
            document.category = str(category_name)
            document.save()
        
        return document


class DocumentStatsSerializer(serializers.Serializer):
    """Serializer for document statistics"""
    
    total_documents = serializers.IntegerField()
    total_categories = serializers.IntegerField()
    recent_uploads = serializers.IntegerField()
    file_types = serializers.DictField()
    category_distribution = serializers.ListField()
    storage_info = serializers.DictField()


class DocumentUsageSerializer(serializers.Serializer):
    """Serializer for document usage analytics"""
    
    most_accessed_documents = serializers.ListField()
    popular_search_terms = serializers.ListField()
    category_usage = serializers.ListField()
    access_patterns = serializers.DictField()