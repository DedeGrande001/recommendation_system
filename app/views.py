"""
Views for recommendation system
"""
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from .forms import RegisterForm, LoginForm, DataUploadForm
from .models import Movie, Rating, RecommendationData, RawDataset
import os
from django.conf import settings


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Registration failed. Please check the form.')
    else:
        form = RegisterForm()

    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()

    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


@login_required
def dashboard_view(request):
    """Main dashboard view"""
    from django.db.models import Avg

    total_movies = Movie.objects.count()
    total_recommendations = RecommendationData.objects.count()
    total_datasets = RawDataset.objects.count()
    processed_datasets = RawDataset.objects.filter(processed=True).count()

    # Calculate average rating
    avg_rating_dict = Movie.objects.aggregate(avg_rating=Avg('avg_rating'))
    avg_rating = avg_rating_dict['avg_rating'] or 0

    # Get top rated movies
    recent_recommendations = RecommendationData.objects.select_related('movie').all()[:10]

    context = {
        'total_movies': total_movies,
        'total_recommendations': total_recommendations,
        'total_datasets': total_datasets,
        'processed_datasets': processed_datasets,
        'avg_rating': avg_rating,
        'recent_recommendations': recent_recommendations,
    }
    return render(request, 'dashboard.html', context)


@login_required
def recommendations_view(request):
    """View all movie recommendations with pagination"""
    # Get genre filter if provided
    genre_filter = request.GET.get('genre', '')

    recommendations_list = RecommendationData.objects.select_related('movie').all()

    # Filter by genre if specified
    if genre_filter:
        recommendations_list = recommendations_list.filter(movie__genres__icontains=genre_filter)

    # Pagination
    paginator = Paginator(recommendations_list, 20)
    page_number = request.GET.get('page')
    recommendations = paginator.get_page(page_number)

    # Get unique genres for filter dropdown
    all_genres = set()
    for movie in Movie.objects.exclude(genres__isnull=True).exclude(genres=''):
        if movie.genres:
            genres_list = movie.genres.split('|')
            all_genres.update(genres_list)

    context = {
        'recommendations': recommendations,
        'all_genres': sorted(all_genres),
        'selected_genre': genre_filter,
    }
    return render(request, 'recommendations.html', context)


@login_required
def data_management_view(request):
    """Data management view for uploading and processing datasets"""
    if request.method == 'POST':
        form = DataUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['data_file']

            # Save file to data directory
            data_dir = os.path.join(settings.BASE_DIR, 'data')
            os.makedirs(data_dir, exist_ok=True)

            file_path = os.path.join(data_dir, uploaded_file.name)
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Create database record
            dataset = RawDataset.objects.create(
                data_file=uploaded_file.name,
                processed=False
            )

            messages.success(request, f'Dataset "{uploaded_file.name}" uploaded successfully!')
            return redirect('data_management')
        else:
            messages.error(request, 'Upload failed. Please check the form.')
    else:
        form = DataUploadForm()

    datasets = RawDataset.objects.all()

    context = {
        'form': form,
        'datasets': datasets,
    }
    return render(request, 'data_management.html', context)


@login_required
def process_dataset_view(request, dataset_id):
    """Trigger Spark processing for a specific dataset"""
    try:
        dataset = RawDataset.objects.get(id=dataset_id)

        messages.info(request, f'Started processing dataset: {dataset.data_file}. This may take several minutes...')

        # Call Spark processing script
        try:
            import subprocess
            spark_script = os.path.join(settings.BASE_DIR, 'spark_jobs', 'spark_to_django.py')

            # Run Spark processing in background
            result = subprocess.run(
                ['python', spark_script],
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            if result.returncode == 0:
                dataset.processed = True
                dataset.save()
                messages.success(request, f'Dataset processing completed! Recommendations generated successfully.')
            else:
                messages.error(request, f'Processing failed: {result.stderr[:200]}')

        except subprocess.TimeoutExpired:
            messages.error(request, 'Processing timeout. Dataset is too large, please run Spark script manually from command line.')
        except Exception as e:
            messages.error(request, f'Processing error: {str(e)}')

        return redirect('data_management')
    except RawDataset.DoesNotExist:
        messages.error(request, 'Dataset does not exist.')
        return redirect('data_management')


@login_required
def delete_dataset_view(request, dataset_id):
    """Delete a single uploaded dataset"""
    if request.method == 'POST':
        try:
            dataset = RawDataset.objects.get(id=dataset_id)
            filename = dataset.data_file

            # Delete physical file
            file_path = os.path.join(settings.BASE_DIR, 'data', filename)
            if os.path.exists(file_path):
                os.remove(file_path)

            # Delete database record
            dataset.delete()

            messages.success(request, f'Successfully deleted dataset: {filename}')
        except RawDataset.DoesNotExist:
            messages.error(request, 'Dataset does not exist')
        except Exception as e:
            messages.error(request, f'Deletion failed: {str(e)}')

    return redirect('data_management')


@login_required
def clear_all_data_view(request):
    """Clear all movie and recommendation data"""
    if request.method == 'POST':
        try:
            # Delete all data
            movie_count = Movie.objects.count()
            rec_count = RecommendationData.objects.count()

            Movie.objects.all().delete()
            RecommendationData.objects.all().delete()

            messages.success(request, f'Successfully cleared data! Deleted {movie_count:,} movies and {rec_count:,} recommendations.')
        except Exception as e:
            messages.error(request, f'Data clearing failed: {str(e)}')

    return redirect('data_management')


@login_required  
def process_progress_view(request):
    """API endpoint for checking processing progress"""
    from django.http import JsonResponse

    # Progress tracking logic can be implemented here
    # Currently returns mock data
    return JsonResponse({
        'status': 'processing',
        'progress': 50,
        'message': 'Processing data...'
    })


@login_required
def process_movielens_view(request):
    """Process MovieLens dataset with background processing and no timeout limit"""
    from django.http import JsonResponse
    import subprocess
    import threading

    if request.method == 'POST':
        try:
            spark_script = os.path.join(settings.BASE_DIR, 'spark_jobs', 'spark_to_django.py')

            # Run in background thread to avoid blocking
            def run_spark():
                try:
                    # No timeout limit to allow processing of any data size
                    result = subprocess.Popen(
                        ['python', spark_script],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    # Don't wait for result, fully asynchronous
                    return True
                except Exception as e:
                    print(f"Spark startup failed: {e}")
                    return False

            # Start background thread (daemon=True runs it in background)
            thread = threading.Thread(target=run_spark, daemon=True)
            thread.start()

            return JsonResponse({
                'success': True,
                'message': 'Spark processing started in background! Processing large files may take 5-10 minutes, please refresh the page later to see results.'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Startup failed: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request'})


@login_required
def personalized_recommendations_view(request):
    """View personalized recommendations for a specific user"""
    user_id = request.GET.get('user_id', 1)

    try:
        user_id = int(user_id)
    except ValueError:
        user_id = 1

    # Get recommendations for this user
    recommendations_list = RecommendationData.objects.filter(
        user_id=user_id
    ).select_related('movie').order_by('-recommendation_score')

    # Pagination
    paginator = Paginator(recommendations_list, 20)
    page_number = request.GET.get('page')
    recommendations = paginator.get_page(page_number)

    # Get statistics
    total_recommendations = recommendations_list.count()

    context = {
        'recommendations': recommendations,
        'user_id': user_id,
        'total_recommendations': total_recommendations,
    }
    return render(request, 'personalized_recommendations.html', context)


def user_recommendations_api(request, user_id):
    """API endpoint to get recommendations for a specific user (public access)"""
    from django.http import JsonResponse

    # Get top N recommendations for user
    try:
        limit = int(request.GET.get('limit', 10))
    except ValueError:
        limit = 10

    recommendations = RecommendationData.objects.filter(
        user_id=user_id
    ).select_related('movie').order_by('-recommendation_score')[:limit]

    results = []
    for rec in recommendations:
        results.append({
            'movie_id': rec.movie.movie_id,
            'title': rec.movie.title,
            'genres': rec.movie.genres,
            'year': rec.movie.year,
            'predicted_rating': round(rec.recommendation_score, 2),
            'avg_rating': round(rec.movie.avg_rating, 2),
            'rating_count': rec.movie.rating_count,
        })

    return JsonResponse({
        'user_id': user_id,
        'recommendations': results,
        'count': len(results)
    })


@login_required
def hive_data_view(request):
    """查看 Hive 中的清洗数据"""
    from .hive_utils import get_hive_statistics, get_top_rated_movies_from_hive, check_hive_connection

    # 检查连接
    connected, connection_msg = check_hive_connection()

    # 获取统计信息
    hive_stats = None
    top_movies = []
    error_msg = None

    if connected:
        hive_stats = get_hive_statistics()

        if hive_stats['available']:
            # 获取 Top 电影
            top_movies, error = get_top_rated_movies_from_hive(limit=10)
            if error:
                error_msg = f"获取电影数据失败: {error}"
        else:
            error_msg = hive_stats.get('error', '无法获取 Hive 数据')
    else:
        error_msg = f"Hive 连接失败: {connection_msg}"

    context = {
        'connected': connected,
        'hive_stats': hive_stats,
        'top_movies': top_movies,
        'error_msg': error_msg,
    }

    return render(request, 'hive_data.html', context)


@login_required
def run_hive_cleaning_view(request):
    """触发 Hive 数据清洗流程"""
    from django.http import JsonResponse
    import subprocess
    import threading

    if request.method == 'POST':
        try:
            # Hive 清洗脚本路径
            cleaning_script = os.path.join(settings.BASE_DIR, 'hive_data_pipeline.py')

            # 检查脚本是否存在
            if not os.path.exists(cleaning_script):
                return JsonResponse({
                    'success': False,
                    'message': f'清洗脚本不存在: {cleaning_script}'
                })

            # 在后台线程运行清洗任务
            def run_cleaning():
                try:
                    result = subprocess.Popen(
                        ['python', cleaning_script],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True
                    )
                    return True
                except Exception as e:
                    print(f"Hive cleaning failed: {e}")
                    return False

            # 启动后台线程
            thread = threading.Thread(target=run_cleaning, daemon=True)
            thread.start()

            return JsonResponse({
                'success': True,
                'message': 'Hive 数据清洗已启动！这可能需要 5-10 分钟，请稍后刷新页面查看结果。'
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'启动失败: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': '无效的请求方法'})


@login_required
def hive_cleaning_progress_view(request):
    """获取 Hive 数据清洗进度"""
    from django.http import JsonResponse
    import json

    progress_file = os.path.join(settings.BASE_DIR, 'hive_cleaning_progress.json')

    try:
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            return JsonResponse(progress_data)
        else:
            # 没有进度文件,返回未开始状态
            return JsonResponse({
                'percentage': 0,
                'current_step': '未开始',
                'message': '还未开始清洗',
                'status': 'idle',
                'timestamp': ''
            })
    except Exception as e:
        return JsonResponse({
            'percentage': 0,
            'current_step': '错误',
            'message': f'读取进度失败: {str(e)}',
            'status': 'error',
            'timestamp': ''
        })
