from django.shortcuts import render


def trang_chu(request):
    return render(request, "chung/trang_chu.html")
