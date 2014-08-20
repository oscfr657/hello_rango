from django.shortcuts import render, render_to_response
from django.shortcuts import redirect
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from datetime import datetime
from .models import Category, Page
from .forms import CategoryForm, PageForm, UserProfileForm, UserForm
from .bing_search import run_query
# Create your views here.


def get_category_list(max_results=3, starts_with=''):

    category_list = []

    if starts_with:
        category_list = Category.objects.filter(name__istartswith=starts_with)
    else:
        category_list = Category.objects.all()

    if max_results > 0:
        if len(category_list) > max_results:
            category_list = category_list[:max_results]

    for category in category_list:
        category.url = category.name.replace(' ', '_')

    return category_list


def index(request):

    context = RequestContext(request)

    context_dict = {'categories': get_category_list()}

    top_pages = Page.objects.order_by('-views')[:5]
    context_dict['top_pages'] = top_pages
    if request.session.get('last_visit'):
        # The session has a value for the last visit
        last_visit_time = request.session.get('last_visit')
        visits = request.session.get('visits', 0)

        if (datetime.now() - datetime.strptime(last_visit_time[:-7], "%Y-%m-%d %H:%M:%S")).days > 0:
            request.session['visits'] = visits + 1
            request.session['last_visit'] = str(datetime.now())
    else:
        # The get returns None, and the session does not have a value for the last visit.
        request.session['last_visit'] = str(datetime.now())
        request.session['visits'] = 1
    #### END NEW CODE ####

    return render_to_response('rango/index.html', context_dict, context)


def about(request):
    context = RequestContext(request)

    if request.session.get('visits'):
        count = request.session.get('visits')
    else:
        count = 0

    return render_to_response('rango/about.html',
                              {'count':count,
                               'categories': get_category_list()},
                              context)


def category(request, category_name_url):
    context = RequestContext(request)

    category_name = category_name_url.replace('_', ' ')

    context_dict = {'category_name': category_name}

    if request.method == 'POST':
        if request.POST.get('query'):
            query = category_name
            query += " "
            query += request.POST['query'].strip()

            if query:
                result_list = []

                result_list = run_query(query)

                if result_list:
                    context_dict['result_list'] = result_list

    try:
        category = Category.objects.get(name=category_name)

        pages = Page.objects.filter(category=category).order_by('-views')


        context_dict['categories'] = get_category_list()

        context_dict['pages'] = pages

        context_dict['category'] = category

        context_dict['category_name_url'] = category_name_url

    except Category.DoesNotExist:
        raise Http404

    return render_to_response('rango/category.html', context_dict, context)


def like_category(request):
    context = RequestContext(request)
    if request.method == 'GET':
        if request.GET['category_id']:
            cat_id = request.GET['category_id']
            likes = 0
            if cat_id:
                category = Category.objects.get(id=int(cat_id))
                if category:
                    category.likes = category.likes + 1
                    likes = category.likes
                    category.save()
            return HttpResponse(likes)


def suggest_category(request):
    context = RequestContext(request)
    list = []
    starts_with = ''
    if request.method == 'GET':
        starts_with = request.GET['suggestion']

    list = get_category_list(8, starts_with)

    return render_to_response('rango/category_search.html',
                              {'cat_search': list },
                              context)


def add_category(request):
    context = RequestContext(request)
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save(commit=True)
            return index(request)
        else:
            print(form.errors)
    else:
        form = CategoryForm()
    return render_to_response('rango/add_category.html',
                              {'form': form,
                               'categories': get_category_list()},
                              context)


def add_page(request, category_name_url):

    context = RequestContext(request)

    category_name = category_name_url.replace('_', ' ')

    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            page = form.save(commit=False)

            try:
                category_name = Category.objects.get(name=category_name)
                page.category = category_name
            except Category.DoesNotExist:

                return render_to_response('rango/add_category.html',
                                          {'categories': get_category_list()},
                                          context)

            page.views = 0

            page.save()
            return redirect('category',category_name_url)
        else:
            print(form.errors)
    else:
        form = PageForm()

    return render_to_response('rango/add_page.html',
                              {'category_name_url': category_name_url,
                               'category_name': category_name,
                               'form': form,
                               'categories': get_category_list()},
                              context)


def register(request):


    context = RequestContext(request)

    registered = False

    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()         #? user_form.save(commit=False)
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            profile.save()

            registered = True

        else:
            print(user_form.errors, profile_form.errors)

    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    return render_to_response(
        'rango/register.html',
        {'user_form':user_form,
         'profile_form':profile_form,
         'registered':registered,
         'categories': get_category_list()},
        context)


def user_login(request):
    context = RequestContext(request)

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request,user)
                return HttpResponseRedirect('/rango/')
            else:
                return HttpResponse("Your Rango account is disabled")
        else:
            print("Invalid login details supplied: {0}, {1}".format(username, password))
            return HttpResponse("Inavlid")
    else:
        return render_to_response('rango/login.html', {'categories': get_category_list()}, context)


@login_required
def restricted(request):
    return HttpResponse("Since you're logged in, you can se this text!")


@login_required
def user_logout(request):
    logout(request)

    return  HttpResponseRedirect('/rango/')

def search(request):
    context = RequestContext(request)
    result_list = []

    if request.method == 'POST':
        query = request.POST['query'].strip()

        if query:
            result_list = run_query(query)

    return render_to_response('rango/search.html',
                              {'result_list':result_list,
                               'categories': get_category_list()},
                              context)

def track_url(request):
    context = RequestContext(request)

    url = '/rango/'
    if request.method == 'GET':
        if 'page_id' in request.GET:
            page_id = request.GET['page_id']
            try:
                page = Page.objects.get(id=page_id)
                page.views = page.views + 1
                page.save()
                url = page.url
            except:
                print('track_url' + url)

    return redirect(url)