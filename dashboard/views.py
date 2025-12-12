from django.shortcuts import render
from rest_framework import status
from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from dashboard.models import PermissionSetup
from orders.models import Order_Table,OrderDetail,Customer_State
from orders.serializers import OrderDetailSerializer,OrderTableSerializer
from accounts.models import Employees,UserTargetsDelails,User
from accounts.serializers import UserProfileSerializer,UserSerializer
from .serializers import PermissionSetupSerializer, UserDetailForDashboard,OrderSerializerDashboard
from django.db.models import Count, OuterRef, Subquery, Sum, F
from utils.custom_logger import setup_logging
from django.utils import timezone
from django.db.models import Q
from django.db.models import Count
import pdb
from datetime import time
import traceback
from datetime import datetime
import calendar 
import logging
logger = logging.getLogger(__name__)
setup_logging(log_file='logs/dashboard_view.log', log_level=logging.WARNING)

class GetUserDashboardtiles(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        dashboard = ScheduleOrderForDashboard()
        _branch = request.user.profile.branch_id
        start_datetime, end_datetime = dashboard.get_date_range(request)
        if 'branch' in request.GET and request.GET['branch']:
            _branch = request.GET['branch']
        agent_ids = Employees.objects.filter(manager=request.user.id).values_list('user', flat=True)
        user_ids_for_manager = Employees.objects.filter(Q(teamlead__in=agent_ids) | Q(user=request.user.id)).values_list('user', flat=True)
        user_ids_for_manager = set(user_ids_for_manager) | set(agent_ids)
        user_ids_for_manager = list(user_ids_for_manager)
        
        user_ids_for_teamlead = list(Employees.objects.filter(teamlead=request.user.id).values_list('user', flat=True))
        user_ids_for_teamlead.append(request.user.id)
        tiles_count = {}

        # Helper function to get base query based on permissions
        def get_base_query(user_perm, all_perm, manager_perm, teamlead_perm, user_id, branch, company, user_ids_manager, user_ids_teamlead):
            
            
            if all_perm or request.user.profile.user_type=='admin':
                return Order_Table.objects.filter(
                    branch=branch,
                    company=company,
                    is_deleted=False
                )
            
            
            elif manager_perm:
                return Order_Table.objects.filter(
                    Q(order_created_by__in=user_ids_manager) | Q(updated_by__in=user_ids_manager),
                    branch=branch,
                    company=company,
                    is_deleted=False
                )
            elif teamlead_perm:
                return Order_Table.objects.filter(
                     Q(order_created_by__in=user_ids_teamlead) | Q(updated_by__in=user_ids_teamlead),
                    branch=branch,
                    company=company,
                    is_deleted=False
                )
            elif user_perm:
               
                return Order_Table.objects.filter(
                    Q(order_created_by=user_id) | Q(updated_by=user_id),
                    branch=branch,
                    company=company,
                    is_deleted=False
                )
            return None

        # Helper function to apply date filter
        def apply_date_filter(query, start_datetime, end_datetime,type=None):
            if request.user.profile.user_type=='admin' and type!=None:
                return query.filter(
                    Q(created_at__range=(start_datetime, end_datetime)),
                    is_deleted=False,
                ).count()
            return query.filter(
                Q(created_at__range=(start_datetime, end_datetime)) |
                Q(updated_at__range=(start_datetime, end_datetime)),
                is_deleted=False,
            ).count()
            return query.filter(
                Q(created_at__range=(start_datetime, end_datetime)) | 
                Q(updated_at__gt=F('created_at'), updated_at__range=(start_datetime, end_datetime))
            ).count()

        # Running tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_running_tile") 
            or request.user.has_perm("dashboard.view_manager_dashboard_running_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_running_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_running_tile")
            or request.user.profile.user_type=='admin'
        ):
            
            if request.user.has_perm("dashboard.view_all_dashboard_running_tile") or request.user.profile.user_type=='admin':
                base_query = Order_Table.objects.filter(
                    branch=_branch,
                    company=request.user.profile.company,
                    # created_at__range=(start_datetime, end_datetime),
                )
            elif request.user.has_perm("dashboard.view_manager_dashboard_running_tile"):
                base_query = Order_Table.objects.filter(
                    Q(order_created_by__in=user_ids_for_manager) | Q(updated_by__in=user_ids_for_manager),
                    branch=_branch,
                    company=request.user.profile.company,
                    # created_at__range=(start_datetime, end_datetime),
                )
            elif request.user.has_perm("dashboard.view_teamlead_dashboard_running_tile"):
                base_query = Order_Table.objects.filter(
                    Q(order_created_by__in=user_ids_for_teamlead) | Q(updated_by__in=user_ids_for_teamlead),
                    branch=_branch,
                    company=request.user.profile.company,
                    # created_at__range=(start_datetime, end_datetime),
                )
            elif request.user.has_perm("dashboard.view_own_dashboard_running_tile"):
                base_query = Order_Table.objects.filter(
                    
                    Q(order_created_by=request.user.id) | Q(updated_by=request.user.id),
                    branch=_branch,
                    company=request.user.profile.company,
                    # created_at__range=(start_datetime, end_datetime),
                )
            # apply_date_filter(base_query, start_datetime, end_datetime)
            tiles_count["running_tile_count"] = {"name":"Running Tile","count":apply_date_filter(base_query, start_datetime, end_datetime,request.user.profile.user_type),"url":''}
        #pending tile
        if (
            request.user.has_perm("dashboard.view_own_dashboard_pending_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_pending_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_pending_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_pending_tile")
            or request.user.profile.user_type=='admin'
        ): 
            
            if request.user.has_perm("dashboard.view_all_dashboard_pending_tile") or request.user.profile.user_type=='admin':
                base_query = Order_Table.objects.filter(
                    branch=_branch,
                    order_status__name="Pending",
                    # created_at__range=(start_datetime, end_datetime),
                )
            
            
            elif request.user.has_perm("dashboard.view_manager_dashboard_pending_tile"):
                base_query = Order_Table.objects.filter(
                    Q(order_created_by__in=user_ids_for_manager) | Q(updated_by__in=user_ids_for_manager),
                    order_status__name="Pending",
                    branch=_branch,
                    company=request.user.profile.company,
                    # created_at__range=(start_datetime, end_datetime),
                )
            elif request.user.has_perm("dashboard.view_teamlead_dashboard_pending_tile"):
                base_query = Order_Table.objects.filter(
                    Q(order_created_by__in=user_ids_for_teamlead) | Q(updated_by__in=user_ids_for_teamlead),
                    order_status__name="Pending",
                    branch=_branch,
                    company=request.user.profile.company,
                    # created_at__range=(start_datetime, end_datetime),
                )
            elif request.user.has_perm("dashboard.view_own_dashboard_pending_tile"):
                base_query = Order_Table.objects.filter(
                     Q(order_created_by=request.user.id) | Q(updated_by=request.user.id),
                    branch=_branch,
                    order_status__name='Pending',
                    # created_at__range=(start_datetime, end_datetime),
                )
            tiles_count["pending_tile_count"] = {"name":"Pending Tile","count":apply_date_filter(base_query, start_datetime, end_datetime,request.user.profile.user_type),"url":'Pending'}

        # Accepted tile count
        
        if (
            request.user.has_perm("dashboard.view_own_dashboard_accepted_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_accepted_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_accepted_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_accepted_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_accepted_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_accepted_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_accepted_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_accepted_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="Accepted")
                tiles_count["accepted_tile_count"] = {"name":"Accepted Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'Accepted'}
            else:
                tiles_count["accepted_tile_count"] = {"name":"Accepted Tile","count":0,"url":'Accepted'}
        #reject tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_rejected_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_rejected_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_rejected_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_rejected_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_rejected_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_rejected_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_rejected_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_rejected_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="Rejected")
                tiles_count["rejected_tile_count"] =  {"name":"Rejected Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'Rejected'}
            else:
                tiles_count["rejected_tile_count"] =  {"name":"Rejected Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'Rejected'}
        # No response tile coun"
        if (
            request.user.has_perm("dashboard.view_all_dashboard_no_response_tile")
            or request.user.has_perm("dashboard.view_own_dashboard_no_response_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_no_response_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_no_response_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_no_response_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_no_response_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_no_response_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_no_response_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="No Response")
                tiles_count["no_response_tile_count"] = {"name":"No Response Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'No Response'}
                tiles_count["no_response_tile_count"] = {"name":"No Response Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'No Response'}

        # Future tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_future_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_future_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_future_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_future_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_future_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_future_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_future_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_future_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="Future Order")
                tiles_count["future_tile_count"] = {"name":"Future Order Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'Future Order'}
            else:
                tiles_count["future_tile_count"] = {"name":"Future Order Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'Future Order'}
        
        # Non-serviceable tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_non_serviceable_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_non_serviceable_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_non_serviceable_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_non_serviceable_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_non_serviceable_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_non_serviceable_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_non_serviceable_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_non_serviceable_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="Non Serviceable")
                tiles_count["non_serviceable_tile_count"] ={"name":"Non Serviceable Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'Non Serviceable'}
            else:
                tiles_count["non_serviceable_tile_count"] = {"name":"Non Serviceable Tile","count":0,"url":'Non Serviceable'}

        # pickup pending_tile tile count      
        if (
            request.user.has_perm("dashboard.view_all_dashboard_pendingspickup_tile")
            or request.user.has_perm("dashboard.view_own_dashboard_ppendingspickup_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_pendingspickup_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_pendingspickup_tile")
            or request.user.profile.user_type=='admin'
            ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_pendingspickup_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_pendingspickup_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_pendingspickup_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_pendingspickup_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="PICKUP PENDING")
                tiles_count["PICKUP_PENDING_tile_count"] = {"name":"PICKUP PENDING Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'PICKUP PENDING'}
            else:
                tiles_count["PICKUP_PENDING_tile_count"] = {"name":"PICKUP PENDING Tile","count":0,"url":'PICKUP PENDING'}

         # In-transit tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_in_transit_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_in_transit_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_in_transit_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_in_transit_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_in_transit_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_in_transit_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_in_transit_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_in_transit_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="IN TRANSIT")
                tiles_count["in-transit_tile_count"] = {"name":"IN TRANSIT Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'IN TRANSIT'}
            else:
                tiles_count["in-transit_tile_count"] = {"name":"IN TRANSIT Tile","count":0,"url":'IN TRANSIT'}

        # OFD tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_ofd_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_ofd_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_ofd_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_ofd_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_ofd_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_ofd_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_ofd_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_ofd_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="OUT FOR DELIVERY")
                tiles_count["OFD_tile_count"] = {"name":"OFD Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'OUT FOR DELIVERY'}
            else:
                tiles_count["OFD_tile_count"] = {"name":"OFD Tile","count":0,"url":'OUT FOR DELIVERY'}
        

        # Delivered tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_delivered_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_delivered_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_delivered_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_delivered_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_delivered_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_delivered_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_delivered_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_delivered_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="DELIVERED")
                tiles_count["delivered_tile_count"] ={"name":"DELIVERED Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'DELIVERED'}
            else:
                tiles_count["delivered_tile_count"] = {"name":"DELIVERED Tile","count":0,"url":'DELIVERED'}


        # In-transit RTO tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_initiatedrto")
            or request.user.has_perm("dashboard.view_all_dashboard_initiatedrto")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_initiatedrto")
            or request.user.has_perm("dashboard.view_manager_dashboard_initiatedrto")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_initiatedrto"),
                request.user.has_perm("dashboard.view_all_dashboard_initiatedrto"),
                request.user.has_perm("dashboard.view_manager_dashboard_initiatedrto"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_initiatedrto"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="RTO INITIATED")
                tiles_count["RTO_INITIATED_tile_count"] = {"name":"RTO INITIATED Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'RTO INITIATED'}
            else:
                tiles_count["RTO_INITIATED_tile_count"] = {"name":"RTO INITIATED Tile","count":0,"url":'RTO INITIATED'}

        # rtodelivered_tile tile count
        if (
            request.user.has_perm("dashboard.view_all_dashboard_rtodelivered_tile")
            or request.user.has_perm("dashboard.view_own_dashboard_rtodelivered_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_rtodelivered_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_rtodelivered_tile")
            or request.user.profile.user_type=='admin'
            ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_rtodelivered_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_rtodelivered_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_rtodelivered_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_rtodelivered_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="RTO DELIVERED")
                tiles_count["rtodelivered_tile_count"] = {"name":"RTO DELIVERED Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'RTO DELIVERED'}
            else:
                tiles_count["rtodelivered_tile_count"] = {"name":"RTO DELIVERED Tile","count":0,"url":'RTO DELIVERED'}

        # EXCEPTION tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_exception_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_exception_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_exception_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_exception_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_exception_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_exception_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_exception_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_exception_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="EXCEPTION")
                tiles_count["EXCEPTION_tile_count"] = {"name":"EXCEPTION Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'EXCEPTION'}
            else:
                tiles_count["EXCEPTION_tile_count"] = {"name":"EXCEPTION Tile","count":0,"url":'EXCEPTION'}

        # NDR tile count
        if (
            request.user.has_perm("dashboard.view_own_dashboard_ndr_tile")
            or request.user.has_perm("dashboard.view_all_dashboard_ndr_tile")
            or request.user.has_perm("dashboard.view_manager_dashboard_ndr_tile")
            or request.user.has_perm("dashboard.view_teamlead_dashboard_ndr_tile")
            or request.user.profile.user_type=='admin'
        ):
            base_query = get_base_query(
                request.user.has_perm("dashboard.view_own_dashboard_ndr_tile"),
                request.user.has_perm("dashboard.view_all_dashboard_ndr_tile"),
                request.user.has_perm("dashboard.view_manager_dashboard_ndr_tile"),
                request.user.has_perm("dashboard.view_teamlead_dashboard_ndr_tile"),
                request.user.id, _branch, request.user.profile.company,
                user_ids_for_manager, user_ids_for_teamlead
            )
            if base_query:
                base_query = base_query.filter(order_status__name="NDR")
                tiles_count["NDR_tile_count"] = {"name":"NDR Tile","count":apply_date_filter(base_query, start_datetime, end_datetime),"url":'NDR'}
            else:
                # If query is empty, set the count to 0
                tiles_count["NDR_tile_count"] = {"name":"NDR Tile","count":0,"url":'NDR'}
        

        
        
       
        
        return Response(
            {
                "status": True,
                "message": "Data fetched successfully",
                "data": tiles_count,
                "errors": None,
            },
            status=status.HTTP_200_OK,
        )
# from django.db.models import Q, Count
# from rest_framework.views import APIView
# from rest_framework.response import Response
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated

# # ------------- replace with your real import  ------------------
# # from .utils import ScheduleOrderForDashboard
# from .models import Order_Table, Employees


class GetUserDashboardtiles1(APIView):
    permission_classes = [IsAuthenticated]

    # ----------------------------------------------------------
    # 1. Map tile key -> (status__name, permission_suffix)
    # ----------------------------------------------------------
    TILES = {
        "running":          (None,                "running_tile"),
        "pending":          ("Pending",           "pending_tile"),
        "accepted":         ("Accepted",          "accepted_tile"),
        "rejected":         ("Rejected",          "rejected_tile"),
        "no_response":      ("No Response",       "no_response_tile"),
        "future":           ("Future Order",      "future_tile"),
        "non_serviceable":  ("Non Serviceable",   "non_serviceable_tile"),
        "pickup_pending":   ("PICKUP PENDING",    "pendingspickup_tile"),
        "in_transit":       ("IN TRANSIT",        "in_transit_tile"),
        "ofd":              ("OUT FOR DELIVERY",  "ofd_tile"),
        "delivered":        ("DELIVERED",         "delivered_tile"),
        "rto_initiated":    ("RTO INITIATED",     "initiatedrto"),
        "rto_delivered":    ("RTO DELIVERED",     "rtodelivered_tile"),
        "exception":        ("EXCEPTION",         "exception_tile"),
        "ndr":              ("NDR",               "ndr_tile"),
    }

    # ----------------------------------------------------------
    # 2. Helpers – 100 % same logic as your original file
    # ----------------------------------------------------------
    def _branch_and_user_ids(self, request):
        """Return branch, dates, manager/team/own user-ids exactly like original."""
        dashboard = ScheduleOrderForDashboard()
        branch = request.user.profile.branch_id
        start_dt, end_dt = dashboard.get_date_range(request)

        # branch override from GET (must happen BEFORE scopes are built!)
        if 'branch' in request.GET and request.GET['branch']:
            branch = int(request.GET['branch'])

        agent_ids = list(
            Employees.objects.filter(manager=request.user.id).values_list('user', flat=True)
        )
        mgr = set(agent_ids)
        mgr.update(
            Employees.objects.filter(
                Q(teamlead__in=agent_ids) | Q(user=request.user.id)
            ).values_list('user', flat=True)
        )
        mgr = list(mgr)

        tl = list(
            Employees.objects.filter(teamlead=request.user.id).values_list('user', flat=True)
        )
        tl.append(request.user.id)

        own = [request.user.id]
        return branch, start_dt, end_dt, mgr, tl, own

    def _base_query(self, request, branch, company, mgr, tl, own, status_name):
        """Same as your get_base_query() but status applied later."""
        user = request.user
        is_admin = user.profile.user_type == 'admin'

        # decide base scope
        if is_admin or any(
            user.has_perm(f"dashboard.view_all_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(branch=branch, company=company, is_deleted=False)
        elif any(
            user.has_perm(f"dashboard.view_manager_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(
                Q(order_created_by__in=mgr) | Q(updated_by__in=mgr),
                branch=branch, company=company, is_deleted=False
            )
        elif any(
            user.has_perm(f"dashboard.view_teamlead_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(
                Q(order_created_by__in=tl) | Q(updated_by__in=tl),
                branch=branch, company=company, is_deleted=False
            )
        elif any(
            user.has_perm(f"dashboard.view_own_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(
                Q(order_created_by__in=own) | Q(updated_by__in=own),
                branch=branch, company=company, is_deleted=False
            )
        else:
            qs = Order_Table.objects.none()

        # apply status filter (except "running")
        if status_name is not None:
            qs = qs.filter(order_status__name=status_name)
        return qs

    def _count_and_amount(self, qs, start_dt, end_dt, is_admin,permission):
        """Return both count and total_amount."""
        if is_admin or not permission:
            filtered_qs = qs.filter(created_at__range=(start_dt, end_dt))
        else:
            filtered_qs = qs.filter(Q(created_at__range=(start_dt, end_dt)) | Q(updated_at__range=(start_dt, end_dt)))

        total_orders = filtered_qs.count()
        total_amount = filtered_qs.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        return total_orders, total_amount

    # ----------------------------------------------------------
    # 3. Single GET
    # ----------------------------------------------------------
    def get(self, request):
        is_admin = request.user.profile.user_type == 'admin'
        branch, start_dt, end_dt, mgr, tl, own = self._branch_and_user_ids(request)
        company = request.user.profile.company
        tiles = {}
        permission = request.user.has_perm('accounts.edit_order_others')
        for key, (status_name, suffix) in self.TILES.items():
            # Permission check
            allowed = (
                request.user.has_perm(f"dashboard.view_own_dashboard_{suffix}") or
                request.user.has_perm(f"dashboard.view_all_dashboard_{suffix}") or
                request.user.has_perm(f"dashboard.view_manager_dashboard_{suffix}") or
                request.user.has_perm(f"dashboard.view_teamlead_dashboard_{suffix}") or
                request.user.profile.user_type == 'admin'
            )
            if not allowed:
                continue

            # 🔀 Special logic for "running"
            if key == "running":
                if request.user.has_perm("dashboard.view_all_dashboard_running_tile") or request.user.profile.user_type == 'admin':
                    qs = Order_Table.objects.filter(
                        branch=branch,
                        company=company,
                        is_deleted=False
                    )
                elif request.user.has_perm("dashboard.view_manager_dashboard_running_tile"):
                    qs = Order_Table.objects.filter(
                        Q(order_created_by__in=mgr) | Q(updated_by__in=mgr),
                        branch=branch,
                        company=company,
                        is_deleted=False
                    )
                elif request.user.has_perm("dashboard.view_teamlead_dashboard_running_tile"):
                    qs = Order_Table.objects.filter(
                        Q(order_created_by__in=tl) | Q(updated_by__in=tl),
                        branch=branch,
                        company=company,
                        is_deleted=False
                    )
                elif request.user.has_perm("dashboard.view_own_dashboard_running_tile"):
                    qs = Order_Table.objects.filter(
                        Q(order_created_by__in=own) | Q(updated_by__in=own),
                        branch=branch,
                        company=company,
                        is_deleted=False
                    )
                else:
                    qs = Order_Table.objects.none()
                cnt, amount = self._count_and_amount(qs, start_dt, end_dt, is_admin,permission)
                # cnt = self._count(qs, None, start_dt, end_dt)
                # total_amount = qs.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
            else:
                # Default logic for all other tiles
                qs = self._base_query(request, branch, company, mgr, tl, own, status_name)
                cnt, amount = self._count_and_amount(qs, start_dt, end_dt, is_admin,permission)
                # cnt = self._count(qs, status_name, start_dt, end_dt)
                # total_amount = qs.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0


            tiles[f"{key}_tile_count"] = {
                "name": f"{status_name or 'Running'} Tile",
                "count": cnt,
                "amount":amount,
                "url": status_name or "",
            }

        return Response(
            {"status": True, "message": "Data fetched successfully", "data": tiles, "errors": None},
            status=status.HTTP_200_OK,
        )
        
class TeamOrderListForDashboard(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request, *args, **kwargs):
        data={}
        if (request.user.has_perm("dashboard.view_all_dashboard_team_order_list") or request.user.has_perm("dashboard.view_manager_dashboard_team_order_list") or request.user.has_perm("dashboard.view_own_team_dashboard_team_order_list") or request.user.profile.user_type=='admin'):
            if request.user.has_perm("dashboard.view_all_dashboard_team_order_list") or request.user.profile.user_type=='admin':
                teamlead_ids = Employees.objects.filter(branch=request.user.profile.branch, company=request.user.profile.company).values_list('teamlead', flat=True).distinct() 
                _teamleadTotalOrder=0
                _teamleadDailyTarget=0
                _teamleadTotalLead=0
                _teamleadAcceptedOrder=0
                _teamleadRejectedOrder=0
                _teamleadNoResponse=0 
                for teamlead_id in list(teamlead_ids):
                    if teamlead_id!=None:
                        _teamleaddat = User.objects.filter(id=teamlead_id).first()
                        if _teamleaddat:
                            _teamlead_serialized_data = UserSerializer(_teamleaddat).data
                        agent_ids = Employees.objects.filter(branch=request.user.profile.branch, company=request.user.profile.company,teamlead=teamlead_id).values_list('user', flat=True).distinct()
                        userDetailsDict={}
                        for agent_id in list(agent_ids):
                            user_profile = User.objects.filter(id=agent_id).first()
                            if user_profile:
                                _agent_serialized_data = UserSerializer(user_profile).data
                            _teamleadDailyTarget += _agent_serialized_data['profile']['daily_order_target']
                            _totalOrder = Order_Table.objects.filter(order_created_by=agent_id,branch=request.user.profile.branch,company=request.user.profile.company).count()
                            _teamleadTotalOrder += _totalOrder
                            _acceptedOrder = Order_Table.objects.filter(order_created_by=agent_id,branch=request.user.profile.branch,company=request.user.profile.company,order_status=2).count()
                            _teamleadAcceptedOrder += _acceptedOrder
                            _rejectedOrder = Order_Table.objects.filter(order_created_by=agent_id,branch=request.user.profile.branch,company=request.user.profile.company,order_status=3).count()
                            _noResponse = Order_Table.objects.filter(order_created_by=agent_id,branch=request.user.profile.branch,company=request.user.profile.company,order_status=4).count()
                            userDetailsDict[agent_id]={"id":agent_id,"total_order":_totalOrder,"daily_target":_agent_serialized_data['profile']['daily_order_target'],"name":_agent_serialized_data['username'],"total_Lead":100,"accepted_order":_acceptedOrder,"rejected_order":_rejectedOrder,"no_response":_noResponse}
                            data[teamlead_id]=userDetailsDict
                        userDetailsDict["teamleadTiles"]={"lead_id":teamlead_id,"teamlead_name":_teamlead_serialized_data['username'],"total_order":_teamleadTotalOrder,"daily_target":_teamleadDailyTarget,"total_lead":_teamleadTotalLead,"accepted_order":_teamleadAcceptedOrder,"rejected_order":_teamleadRejectedOrder,"no_response":_teamleadNoResponse}
                        _teamleadTotalOrder, _teamleadDailyTarget, _teamleadTotalLead, _teamleadAcceptedOrder, _teamleadRejectedOrder, _teamleadNoResponse = (0, 0, 0, 0, 0, 0)

            elif request.user.has_perm("dashboard.view_manager_dashboard_team_order_list"):
                pass
            elif request.user.has_perm("dashboard.view_own_team_dashboard_team_order_list"):
                pass
        return Response(
            {
                "status": True,
                "message": "Data fetched successfully",
                "data": data,
                "errors": None,
            },
            status=status.HTTP_200_OK,
        )

class TopShellingProduct(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        _branch = request.user.profile.branch_id
        if 'branch' in request.GET and request.GET['branch']:
            _branch = request.GET['branch']

        month = request.GET.get('month', '').lower()
        year = request.GET.get('year', '')

        orders = Order_Table.objects.filter(
            branch=_branch,
            company=request.user.profile.company
        )

       
        if month and year:
            try:
                month = int(month)
                year = int(year)
                if month < 1 or month > 12:
                    raise ValueError("Month must be between 1 and 12")
                first_day = datetime(year, month, 1)
                last_day = datetime(year, month, calendar.monthrange(year, month)[1])
                last_day = datetime.combine(last_day, time.max)
                orders = orders.filter(created_at__range=(first_day, last_day))
            except ValueError as e:
                return Response({
                    "status": False,
                    "message": "Invalid month or year provided.",
                    "data": [],
                    "errors": str(e)
                }, status=status.HTTP_400_BAD_REQUEST)
        serialized_orders = OrderTableSerializer(orders, many=True).data
        product_summary = self._summarize_products(serialized_orders)

        return Response({
            "status": True,
            "message": "Data fetched successfully",
            "data": product_summary,
            "errors": None,
        }, status=status.HTTP_200_OK)



    def _summarize_products(self, orders):
        product_summary = {}

        for order in orders:
            for product in order['order_details']:
                product_name = product['product_name']
                product_qty = product['product_qty']
                product_mrp = product['product_mrp']
                order_id = product['order']
                total_price = product_mrp * product_qty

                if product_name in product_summary:
                    self._update_product_summary(product_summary[product_name], product_qty, order_id, total_price)
                else:
                    product_summary[product_name] = self._create_new_product_entry(
                        product_qty, total_price, product_mrp, order_id
                    )

        return product_summary

    def _update_product_summary(self, product_data, qty, order_id, total_price):
        if product_data['orderId'] != order_id:
            product_data['order_count'] += 1
            product_data['orderId'] = order_id

        product_data['unit'] += qty
        product_data['total_shell_in_rupee'] = product_data['unit'] * product_data['product_price']

    def _create_new_product_entry(self, qty, total_price, price, order_id):
        return {
            "unit": qty,
            "total_shell_in_rupee": total_price,
            "product_price": price,
            "product_image": "-------------------",
            "orderId": order_id,
            "order_count": 1
        }
from django.db.models import ExpressionWrapper, DecimalField
class TopShellingProduct1(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        branch = int(request.GET.get('branch', request.user.profile.branch_id))
        company = request.user.profile.company
        month = request.GET.get('month', '')
        year = request.GET.get('year', '')

        try:
            if not (month and year):
                today = timezone.now()
                month = today.month
                year = today.year
            else:
                month = int(month)
                year = int(year)
                if not 1 <= month <= 12:
                    raise ValueError("Month must be 1-12")
        except ValueError as e:
            return Response({
                "status": False,
                "message": str(e),
                "data": [],
                "errors": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # Build date range
        first_day = timezone.make_aware(datetime(year, month, 1))
        last_day = timezone.make_aware(
            datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59)
        )

        # Query top-selling products
        qs = (
            OrderDetail.objects
            .select_related('order')
            .filter(
                order__branch=branch,
                order__company=company,
                order__created_at__range=(first_day, last_day),
                order__is_deleted=False
            )
            .values('product_name', 'product_mrp')
            .annotate(
                unit=Sum('product_qty'),
                total_shell_in_rupee=Sum(
                    ExpressionWrapper(F('product_mrp') * F('product_qty'), output_field=DecimalField())
                ),
                order_count=Count('order', distinct=True),
            )
            .order_by('-total_shell_in_rupee')
        )

        # Build response
        data = {
            row['product_name']: {
                "unit": row['unit'],
                "total_shell_in_rupee": float(row['total_shell_in_rupee']),
                "product_price": float(row['product_mrp']),
                "product_image": "-------------------",
                "orderId": OrderDetail.objects
                    .filter(product_name=row['product_name'])
                    .order_by('-id')
                    .values_list('order_id', flat=True)
                    .first(),
                "order_count": row['order_count'],
            }
            for row in qs
        }

        return Response({
            "status": True,
            "message": "Data fetched successfully",
            "data": data,
            "errors": None
        }, status=status.HTTP_200_OK)
    
class ScheduleOrderForDashboard(APIView):
    def get(self, request, *args, **kwargs):
        try:
            _branch = request.user.profile.branch_id
            start_datetime, end_datetime = self.get_date_range(request)
            if 'branch' in request.GET and request.GET['branch']:
                _branch = request.GET['branch']

            scheduled_count = self.get_order_count(is_scheduled=1, branch=_branch, start_datetime=start_datetime, end_datetime=end_datetime)
            non_scheduled_count = self.get_order_count(is_scheduled=0, branch=_branch, start_datetime=start_datetime, end_datetime=end_datetime)
            return Response(
                {
                    "status": True,
                    "message": "Data fetched successfully",
                    "data": {
                        "non_scheduled": non_scheduled_count,
                        "scheduled": scheduled_count,
                    },
                    "errors": None,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"status": False, "message": "An error occurred", "data": {}, "errors": True},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def get_date_range(self, request):
        """Extract and validate the date range from the request."""
        if 'date_range' in request.GET and request.GET['date_range']:
            date_range = request.GET['date_range'].split(' ')
            if len(date_range) != 2:
                raise ValueError("Date Range invalid")
        
            # Parse the start and end dates
            start_date = datetime.fromisoformat(date_range[0]).date()
            end_date = datetime.fromisoformat(date_range[1]).date()
            # If the end date is the same as the start date, adjust the end time to the last moment of the day
            if start_date == end_date:
                end_date = start_date  # Keep the same day
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999
            else:
                end_datetime = datetime.combine(end_date, time.max)  # Set to 23:59:59.999999
            start_datetime = datetime.combine(start_date, time.min)  # Set start time to 00:00:00

            return start_datetime, end_datetime
        else:
            today = datetime.now().date()

            # If no date range is provided, return the full range of today
            start_datetime = datetime.combine(today, time.min)  # Start of today
            end_datetime = datetime.combine(today, time.max)    # End of today

            return start_datetime, end_datetime
        
    def get_date_range_post(self, request):
        """Extract and validate the date range from the request."""
        if 'date_range' in request.data and request.data['date_range']:
            date_range = request.data['date_range'].split(' ')
            if len(date_range) != 2:
                raise ValueError("Date Range invalid")
            start_datetime = datetime.fromisoformat(date_range[0])
            end_datetime = datetime.fromisoformat(date_range[1])
            return start_datetime, end_datetime
        else:
            today = datetime.now()
            return datetime(today.year, today.month, 1), today

    def get_order_count(self, is_scheduled, branch, start_datetime, end_datetime):
        """Count orders based on scheduling status."""
        return Order_Table.objects.filter(
            is_scheduled=is_scheduled,
            branch=branch,
            company=self.request.user.profile.company,
            updated_at__range=(start_datetime, end_datetime),
        ).count()

class StateWiseSalesTracker(APIView):
    def get(self, request, *args: tuple, **kwargs: dict) -> Response:
        try:
            dashboard = ScheduleOrderForDashboard()
            _branch = request.user.profile.branch_id
            start_datetime, end_datetime = dashboard.get_date_range(request)
            if 'branch' in request.GET and request.GET['branch']:
                _branch = request.GET['branch']

            orders_data = (
                Order_Table.objects.filter(
                    branch=_branch,
                    company=request.user.profile.company,
                    updated_at__range=(start_datetime, end_datetime),
                )
                .values('customer_state')
                .annotate(count=Count('id'))
            )

            state_mapping = {state.id: state.name for state in Customer_State.objects.all()}
            state_counts = {
                state_mapping.get(entry['customer_state'], 'Unknown'): entry['count']
                for entry in orders_data
            }

            if not state_counts:
                return Response(
                    {
                        "status": True,
                        "message": "No data found for the specified criteria.",
                        "data": state_counts,
                        "errors": None,
                    },
                    status=status.HTTP_204_NO_CONTENT,
                )

            return Response(
                {
                    "status": True,
                    "message": "Data fetched successfully",
                    "data": state_counts,
                    "errors": None,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            logger.error(f"Error fetching state-wise sales data: {str(e)}")
            logger.error(traceback.format_exc())
            return Response(
                {
                    "status": False,
                    "message": "An error occurred while fetching data.",
                    "data": None,
                    "errors": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
class InvoiceDataForDashboard(APIView):
    def get(self, request, *args: tuple, **kwargs: dict) -> Response:
        dashboard = ScheduleOrderForDashboard()
        _branch = request.user.profile.branch_id

        try:
            start_datetime, end_datetime = dashboard.get_date_range(request)
        except Exception as e:
            logger.error(f"Error fetching date range: {e}")
            return Response(
                {
                    "status": False,
                    "message": "Error fetching date range.",
                    "errors": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if 'branch' in request.GET and request.GET['branch']:
            _branch = request.GET['branch']
        
        try:
            orders_data = Order_Table.objects.filter(
                branch=_branch,
                company=request.user.profile.company,
                updated_at__range=(start_datetime, end_datetime),
            )
        except Exception as e:
            logger.error(f"Error fetching orders data: {e}")
            return Response(
                {
                    "status": False,
                    "message": "Error fetching orders data.",
                    "errors": True,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = {
            'unpaid_amount': {'count': 0, 'amount': 0},
            'paid_amount': {'count': 0, 'amount': 0},
            'cancel_amount': {'count': 0, 'amount': 0},
            'sent_amount': {'count': 0, 'amount': 0},
        }

        if orders_data.exists():
            for row in orders_data:
                try:
                    if (row.payment_status.id == 1 or row.payment_status.id == 3) and row.order_status.id != 3 and row.is_scheduled == 0:
                        data['unpaid_amount']['count'] += 1
                        data['unpaid_amount']['amount'] += (row.gross_amount - row.prepaid_amount)
                    elif row.payment_status.id == 2:
                        data['paid_amount']['count'] += 1
                        data['paid_amount']['amount'] += row.gross_amount
                    elif row.order_status.id == 3:
                        data['cancel_amount']['count'] += 1
                        data['cancel_amount']['amount'] += row.gross_amount
                    elif row.is_scheduled == 1:
                        data['sent_amount']['count'] += 1
                        data['sent_amount']['amount'] += row.gross_amount
                except Exception as e:
                    logger.error(f"Error processing order ID {row.id}: {e}")

        return Response(
            {
                "status": True,
                "message": "Data fetched successfully",
                "data": data,
                "errors": False,
            },
            status=status.HTTP_200_OK,
        )
        
class SalesForecastDashboard(APIView):
    def get(self, request, *args: tuple, **kwargs: dict) -> Response:
        dashboard = ScheduleOrderForDashboard()
        _branch = request.user.profile.branch_id
        if request.user.has_perm("testcontent1.test_permission1"):
            return Response({"name":"han sahi challa he"},status=status.HTTP_200_OK)
        else:
            return Response({"name":"nhi sahi challa he 😔"},status=status.HTTP_403_FORBIDDEN)
            
        try:
            start_datetime, end_datetime = dashboard.get_date_range(request)
        except Exception as e:
            logger.error(f"Error fetching date range: {e}")
            return Response(
                {
                    "status": False,
                    "message": "Error fetching date range.",
                    "errors": True,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if 'branch' in request.GET and request.GET['branch']:
            _branch = request.GET['branch']
        
        try:
            orders_data = Order_Table.objects.filter(
                branch=_branch,
                company=request.user.profile.company,
                updated_at__range=(start_datetime, end_datetime),
            )
        except Exception as e:
            logger.error(f"Error fetching orders data: {e}")
            return Response(
                {
                    "status": False,
                    "message": "Error fetching orders data.",
                    "errors": True,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        data = {}
        if orders_data.exists():
            for row in orders_data:
                try:
                    status_name = row.order_status.name
                    if status_name in data:
                        data[status_name]['count'] += 1
                        data[status_name]['amount'] += row.gross_amount
                    else:
                        data[status_name] = {
                            'count': 1,
                            'amount': row.gross_amount,
                        }
                except Exception as e:
                    logger.error(f"Error processing order with ID {row.id}: {e}")

        return Response(
            {
                "status": True,
                "message": "Data fetched successfully",
                "data": data,
                "errors": False,
            },
            status=status.HTTP_200_OK,
        )







from django.apps import apps
from rest_framework.decorators import action
from rest_framework import viewsets, status
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.apps import apps
from rest_framework.decorators import action

class AllModelsViewSet(viewsets.ViewSet):
    """
    API endpoint to fetch all models from the project.
    """
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='list-all-models')  # ✅ Corrected endpoint
    def list_all_models(self, request):
        """
        Returns all models grouped by their respective apps.
        """
        all_apps = {}
        model_names = []
        for model in apps.get_models():
            app_label = model._meta.app_label  # Get app name
            model_name = model.__name__  # Get model name
            model_names.append(model_name)
            # all_apps[app_label].append(model_name)

        return Response({"data": model_names}, status=200)



from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import PermissionSetup
from .serializers import PermissionSetupSerializer

class PermissionSetupViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def create(self, request):
        
        name = request.data.get("name")
        models_name = request.data.get("models_name")
        role_type = request.data.get("type")

        if not name or not models_name or not role_type:
            return Response({"error": "Missing required fields (name, models_name, type)."}, status=status.HTTP_400_BAD_REQUEST)

        # Create new permission setup entry
        permission_setup = PermissionSetup.objects.create(
            name=name,
            models_name=models_name,
            role_type=role_type
        )

        return Response({"message": "Permission setup created successfully.", "data": PermissionSetupSerializer(permission_setup).data}, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        
        try:
            permission_setup = PermissionSetup.objects.get(id=pk) 

            permission_setup.models_name = request.data.get("models_name", permission_setup.models_name)
            permission_setup.role_type = request.data.get("type", permission_setup.role_type)
            permission_setup.save()

            return Response({"message": "Permission setup updated successfully.", "data": PermissionSetupSerializer(permission_setup).data}, status=status.HTTP_200_OK)
        
        except PermissionSetup.DoesNotExist:
            return Response({"error": "Permission setup not found."}, status=status.HTTP_404_NOT_FOUND)

    def list(self, request):
        
        permission_setups = PermissionSetup.objects.all()
        serializer = PermissionSetupSerializer(permission_setups, many=True)
        return Response({"data": serializer.data}, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
       
        try:
            permission_setup = PermissionSetup.objects.get(id=pk) 
            serializer = PermissionSetupSerializer(permission_setup)
            return Response({"data": serializer.data}, status=status.HTTP_200_OK)
        except PermissionSetup.DoesNotExist:
            return Response({"error": "Permission setup not found."}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, pk=None):
        
        try:
            permission_setup = PermissionSetup.objects.get(id=pk) 
            permission_setup.delete()
            return Response({"message": f"Permission setup with id '{pk}' deleted successfully."}, status=status.HTTP_204_NO_CONTENT)
        
        except PermissionSetup.DoesNotExist:
            return Response({"error": "Permission setup not found."}, status=status.HTTP_404_NOT_FOUND)



class DynamicTabsViewSet(viewsets.ViewSet):
     permission_classes = [IsAuthenticated]
     def list(self, request):
        """
        Get all permission setups.
        """
        role_type = request.user.profile.user_type

        if role_type:
            permission_setups = PermissionSetup.objects.filter(role_type=role_type)
        else:
            pass

        data = {}
        for setup in permission_setups:
            data[setup.name] = setup.models_name
        
        return Response(data, status=status.HTTP_200_OK)


class OrderStatusSummary(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        # 1. branch / company
        branch = int(request.GET.get("branch", request.user.profile.branch_id))
        company = request.user.profile.company

        # 2. month / year
        month = request.GET.get("month", "").lower()
        year = request.GET.get("year", "")

        # default to current month
        if not (month and year):
            today = timezone.now()
            month, year = today.month, today.year
        else:
            try:
                month, year = int(month), int(year)
                if not 1 <= month <= 12:
                    raise ValueError
            except ValueError:
                return Response(
                    {"status": False, "message": "month must be 1-12 and year must be int"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        first_day = timezone.make_aware(datetime(year, month, 1))
        last_day = timezone.make_aware(
            datetime(year, month, calendar.monthrange(year, month)[1], 23, 59, 59)
        )

        # 3. queryset
        qs = (
            Order_Table.objects
            .filter(
                branch=branch,
                company=company,
                is_deleted=False,
                created_at__range=(first_day, last_day),
            )
            .values("order_status__name")                          # group by status
            .annotate(
                total_amount=Sum("total_amount"),
                order_count=Count("id"),
                image_url=F("orderdetail__product__product_image") # first image
            )
            .order_by("-total_amount")
            .distinct()
        )

        # 4. build response
        data = [
            {
                "status": row["order_status__name"],
                "total_amount": row["total_amount"] or 0,
                "order_count": row["order_count"],
                "image": row["image_url"] or "-------------------",
            }
            for row in qs
        ]

        return Response(
            {"status": True, "message": "Data fetched successfully", "data": data, "errors": None},
            status=status.HTTP_200_OK,
        )
    
class GetUserHometiles(APIView):
    permission_classes = [IsAuthenticated]

    # ----------------------------------------------------------
    # 1. Map tile key -> (status__name, permission_suffix)
    # ----------------------------------------------------------
    TILES = {
        "running":          (None,                "running_tile"),
        "pending":          ("Pending",           "pending_tile"),
        "accepted":         ("Accepted",          "accepted_tile"),
        "rejected":         ("Rejected",          "rejected_tile"),
        "no_response":      ("No Response",       "no_response_tile"),
        "future":           ("Future Order",      "future_tile"),
        "non_serviceable":  ("Non Serviceable",   "non_serviceable_tile"),
        "pickup_pending":   ("PICKUP PENDING",    "pendingspickup_tile"),
        "in_transit":       ("IN TRANSIT",        "in_transit_tile"),
        "ofd":              ("OUT FOR DELIVERY",  "ofd_tile"),
        "delivered":        ("DELIVERED",         "delivered_tile"),
        "rto_initiated":    ("RTO INITIATED",     "initiatedrto"),
        "rto_delivered":    ("RTO DELIVERED",     "rtodelivered_tile"),
        "exception":        ("EXCEPTION",         "exception_tile"),
        "ndr":              ("NDR",               "ndr_tile"),
    }

    # ----------------------------------------------------------
    # 2. Helpers – 100 % same logic as your original file
    # ----------------------------------------------------------
    def _branch_and_user_ids(self, request):
        """Return branch, dates, manager/team/own user-ids exactly like original."""
        dashboard = ScheduleOrderForDashboard()
        # branch = request.user.profile.branch_id
        start_dt, end_dt = dashboard.get_date_range(request)

        # branch override from GET (must happen BEFORE scopes are built!)
        # if 'branch' in request.GET and request.GET['branch']:
        #     branch = int(request.GET['branch'])

        agent_ids = list(
            Employees.objects.filter(manager=request.user.id).values_list('user', flat=True)
        )
        mgr = set(agent_ids)
        mgr.update(
            Employees.objects.filter(
                Q(teamlead__in=agent_ids) | Q(user=request.user.id)
            ).values_list('user', flat=True)
        )
        mgr = list(mgr)

        tl = list(
            Employees.objects.filter(teamlead=request.user.id).values_list('user', flat=True)
        )
        tl.append(request.user.id)

        own = [request.user.id]
        return  start_dt, end_dt, mgr, tl, own

    def _base_query(self, request, company, mgr, tl, own, status_name):
        """Same as your get_base_query() but status applied later."""
        user = request.user
        is_admin = user.profile.user_type == 'admin'

        # decide base scope
        if is_admin or any(
            user.has_perm(f"dashboard.view_all_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(company=company, is_deleted=False)
        elif any(
            user.has_perm(f"dashboard.view_manager_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(
                Q(order_created_by__in=mgr) | Q(updated_by__in=mgr), company=company, is_deleted=False
            )
        elif any(
            user.has_perm(f"dashboard.view_teamlead_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(
                Q(order_created_by__in=tl) | Q(updated_by__in=tl),
                company=company, is_deleted=False
            )
        elif any(
            user.has_perm(f"dashboard.view_own_dashboard_{s}")
            for _, s in self.TILES.values()
        ):
            qs = Order_Table.objects.filter(
                Q(order_created_by__in=own) | Q(updated_by__in=own),
                 company=company, is_deleted=False
            )
        else:
            qs = Order_Table.objects.none()

        # apply status filter (except "running")
        if status_name is not None:
            qs = qs.filter(order_status__name=status_name)
        return qs

    def _count_and_amount(self, qs, start_dt, end_dt, is_admin,permission):
        """Return both count and total_amount."""
        if is_admin or not permission:
            filtered_qs = qs.filter(created_at__range=(start_dt, end_dt))
        else:
            filtered_qs = qs.filter(Q(created_at__range=(start_dt, end_dt)) | Q(updated_at__range=(start_dt, end_dt)))

        total_orders = filtered_qs.count()
        total_amount = filtered_qs.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
        return total_orders, total_amount

    # ----------------------------------------------------------
    # 3. Single GET
    # ----------------------------------------------------------
    def get(self, request):
        is_admin = request.user.profile.user_type == 'admin'
        start_dt, end_dt, mgr, tl, own = self._branch_and_user_ids(request)
        company = request.user.profile.company
        tiles = {}
        permission = request.user.has_perm('accounts.edit_order_others')
        for key, (status_name, suffix) in self.TILES.items():
            # Permission check
            allowed = (
                request.user.has_perm(f"dashboard.view_own_dashboard_{suffix}") or
                request.user.has_perm(f"dashboard.view_all_dashboard_{suffix}") or
                request.user.has_perm(f"dashboard.view_manager_dashboard_{suffix}") or
                request.user.has_perm(f"dashboard.view_teamlead_dashboard_{suffix}") or
                request.user.profile.user_type == 'admin'
            )
            if not allowed:
                continue

            # 🔀 Special logic for "running"
            if key == "running":
                if request.user.has_perm("dashboard.view_all_dashboard_running_tile") or request.user.profile.user_type == 'admin':
                    qs = Order_Table.objects.filter(
                       
                        company=company,
                        is_deleted=False
                    )
                elif request.user.has_perm("dashboard.view_manager_dashboard_running_tile"):
                    qs = Order_Table.objects.filter(
                        Q(order_created_by__in=mgr) | Q(updated_by__in=mgr),
                        
                        company=company,
                        is_deleted=False
                    )
                elif request.user.has_perm("dashboard.view_teamlead_dashboard_running_tile"):
                    qs = Order_Table.objects.filter(
                        Q(order_created_by__in=tl) | Q(updated_by__in=tl),
                        
                        company=company,
                        is_deleted=False
                    )
                elif request.user.has_perm("dashboard.view_own_dashboard_running_tile"):
                    qs = Order_Table.objects.filter(
                        Q(order_created_by__in=own) | Q(updated_by__in=own),
                   
                        company=company,
                        is_deleted=False
                    )
                else:
                    qs = Order_Table.objects.none()
                cnt, amount = self._count_and_amount(qs, start_dt, end_dt, is_admin,permission)
                # cnt = self._count(qs, None, start_dt, end_dt)
                # total_amount = qs.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0
            else:
                # Default logic for all other tiles
                qs = self._base_query(request,  company, mgr, tl, own, status_name)
                cnt, amount = self._count_and_amount(qs, start_dt, end_dt, is_admin,permission)
                # cnt = self._count(qs, status_name, start_dt, end_dt)
                # total_amount = qs.aggregate(total_amount=Sum('total_amount'))['total_amount'] or 0


            tiles[f"{key}_tile_count"] = {
                "name": f"{status_name or 'Running'} Tile",
                "count": cnt,
                "amount":amount,
                "url": status_name or "",
            }

        return Response(
            {"status": True, "message": "Data fetched successfully", "data": tiles, "errors": None},
            status=status.HTTP_200_OK,
        )