from django.urls import path

from .views import ChatCompletionsProxyView, FileUploadView

urlpatterns = [
    path('chat/completions', ChatCompletionsProxyView.as_view(), name='chat-completions'),
    path('files/upload', FileUploadView.as_view(), name='file-upload'),
]
