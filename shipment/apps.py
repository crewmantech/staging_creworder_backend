from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.apps import AppConfig




class ShipmentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'shipment'

    def ready(self):
        import logging
        logger = logging.getLogger(__name__)
        print("Shipment App Ready")  # Debug: Indicates app startup

        # Lazy import to prevent early model import errors
        from shipment.models import ShipmentModel
        from orders.models import Order_Table, OrderStatus, AllowStatus, OrderStatusWorkflow
        from services.shipment.schedule_orders import ShiprocketScheduleOrder, TekipostService, NimbuspostAPI,ZoopshipService,EshopboxAPI
        from shipment.serializers import ShipmentSerializer
        from django.db.models import Q
        from services.orders.order_service import trigger_order_status_notifications
        # Mapping vendor-specific status to main system OrderStatus
        def get_main_order_status_for_vendor_status(shipment_vendor, vendor_status_name):
            try:
                allow_status = AllowStatus.objects.get(
                    name__iexact=vendor_status_name,   # ✅ exact match, case-insensitive
                    shipment_vendor=shipment_vendor    # ✅ restrict to vendor
                )
                workflow = OrderStatusWorkflow.objects.filter(
                    shipment_vendor=shipment_vendor,
                    allow_status=allow_status
                ).select_related('order_status').first()

                return workflow.order_status if workflow else None
            except AllowStatus.DoesNotExist:
                return None

        # Main function to fetch and update all shipments from Shiprocket, Tekipost, Nimbuspost
        def fetch_and_update_shipments():
            print("0000000000000in fetch")
            try:
                shipments = ShipmentModel.objects.filter(status=1)
                serializer = ShipmentSerializer(shipments, many=True)
                serialized_data = serializer.data

                for shipmentData in serialized_data:
                    vendor_data = shipmentData['shipment_vendor']
                    vendor_id = vendor_data.get('id')
                    vendor_name = vendor_data.get('name', '').lower()
                    company = shipmentData["company_id"]  # CharField
                    # branch = shipmentData["branch_id"]    # CharField

                    # --- SHIPROCKET ---
                    if vendor_name == 'shiprocket' and shipmentData['credential_username']:
                        shiprocket_service = ShiprocketScheduleOrder(
                            shipmentData['credential_username'],
                            shipmentData['credential_password']
                        )

                        details = shiprocket_service.shipment_details()
                        if details.get("status") != "success":
                            logger.warning(f"Shiprocket fetch failed for vendor ID: {vendor_id}")
                            continue

                        for detail in details.get("shipment_details", {}).get("data", []):
                            order_id = detail.get("order_id")
                            status = detail.get("status")
                            # print(status,"------------------status")
                            try:
                                mapped_status = get_main_order_status_for_vendor_status(vendor_id, status)
                                if mapped_status:
                                    order = Order_Table.objects.get(vendor_order_id=order_id)
                                    order_status, _ = OrderStatus.objects.get_or_create(name=mapped_status.name)
                                    if order.order_status_id != order_status.id:
                                        order.order_status = order_status
                                        order.save()
                                        logger.info(f"[Shiprocket] Updated order {order.id} to status {status}")
                                        try:
                                            trigger_order_status_notifications(company, order_status.id, order.id)
                                        except Exception as e:
                                            print(f"Error triggering order status notification: {e}")
                                            pass  # continue execution silently if needed

                            except Order_Table.DoesNotExist:
                                logger.warning(f"[Shiprocket] Order not found for vendor_order_id: {order_id}")
                            except Exception as e:
                                logger.error(f"[Shiprocket] Error updating order {order_id}: {e}")

                    # --- TEKIPOST ---
                    elif vendor_name == 'tekipost' and shipmentData['credential_username']:
                        takipost_service = TekipostService(
                            shipmentData['credential_username'],
                            shipmentData['credential_password']
                        )
                        excluded_statuses = [
                            'ACCEPTED', 'No Response', 'Future Order', 'Non Serviceable',
                            'DELIVERED', 'RTO DELIVERED', 'EXCEPTION'
                        ]
                        orders = Order_Table.objects.filter(
                            order_wayBill__isnull=False,
                            company=company
                        ).exclude(order_wayBill='').exclude(order_status__name__in=excluded_statuses)

                        for order in orders:
                            try:
                                awb_number = order.order_wayBill
                                response = takipost_service.track_order(awb_number)

                                if response.get("success") and response.get("response") == 1:
                                    shipment_status = response["data"].get("status_name")
                                    if shipment_status:
                                        mapped_status = get_main_order_status_for_vendor_status(vendor_id, shipment_status)
                                        if mapped_status:
                                            order_status, _ = OrderStatus.objects.get_or_create(name=mapped_status.name)
                                            if order.order_status_id != order_status.id:
                                                order.order_status = order_status
                                                order.save()
                                                logger.info(f"[Tekipost] Updated order {order.id} to status {shipment_status}")
                                                try:
                                                    trigger_order_status_notifications(company, order_status.id, order.id)
                                                except Exception as e:
                                                    print(f"Error triggering order status notification: {e}")
                                                    pass 
                            except Exception as e:
                                logger.error(f"[Tekipost] Error updating order {order.id}: {e}")

                    # --- NIMBUSPOST ---
                    elif vendor_name == 'nimbuspost' and shipmentData['credential_username']:
                        nimbuspost_service = NimbuspostAPI(
                            shipmentData['credential_username'],
                            shipmentData['credential_password']
                        )
                        excluded_statuses = [
                            'ACCEPTED', 'No Response', 'Future Order', 'Non Serviceable',
                            'DELIVERED', 'RTO DELIVERED', 'EXCEPTION',"PENDING"
                        ]
                        orders = Order_Table.objects.filter(
                            order_wayBill__isnull=False,
                            company=company
                        ).exclude(order_wayBill='').exclude(order_status__name__in=excluded_statuses)

                        for order in orders:
                            try:
                                
                                awb_number = order.order_wayBill
                                
                                response = nimbuspost_service.track_single_shipment(awb_number)
                                if not response.get("status"):
                                    continue

                                shipment_status = response.get("data", {}).get("status")
                            
                                if shipment_status:
                                    mapped_status = get_main_order_status_for_vendor_status(vendor_id, shipment_status)
                                    if mapped_status:
                                        order_status, _ = OrderStatus.objects.get_or_create(name=mapped_status.name)
                                        if order.order_status_id != order_status.id:
                                            order.order_status = order_status
                                            order.save()
                                            logger.info(f"[Nimbuspost] Updated order {order.id} to status {shipment_status}")
                                            try:
                                                trigger_order_status_notifications(company, order_status.id, order.id)
                                            except Exception as e:
                                                print(f"Error triggering order status notification: {e}")
                                                pass 
                            except Exception as e:
                                logger.error(f"[Nimbuspost] Error updating order {order.id}: {e}")
                    
                    elif vendor_name == 'eshopbox' and shipmentData['credential_username']:
                        print("In Eshopbox-----------------")
                        eshopbox_service = EshopboxAPI(
                            shipmentData['credential_username'],shipmentData['credential_password'],serialized_data['credential_token']
                        )
                        excluded_statuses = [
                            'ACCEPTED', 'No Response', 'Future Order', 'Non Serviceable',
                            'DELIVERED', 'RTO DELIVERED', 'EXCEPTION',"PENDING"
                        ]
                        orders = Order_Table.objects.filter(
                            order_wayBill__isnull=False,
                            company=company
                        ).exclude(order_wayBill='').exclude(order_status__name__in=excluded_statuses)

                        for order in orders:
                            try:
                                
                                awb_number = order.order_wayBill
                                print(awb_number,"------------------AWB NUMBER-------------------")
                                response = eshopbox_service.track_bulk_shipments([awb_number])
                                print(response,"------------------Eshopbox Response-------------------")
                                if response.get("status") != "SUCCESS":
                                    continue

                                shipment_status = response.get("data", {}).get("status")
                                tracking_list = response.get("trackingDetailList", [])
                                if not tracking_list:
                                    continue
                                shipment_status = tracking_list[0].get("currentStatus")
                                if shipment_status:
                                    mapped_status = get_main_order_status_for_vendor_status(vendor_id, shipment_status)
                                    if mapped_status:
                                        order_status, _ = OrderStatus.objects.get_or_create(name=mapped_status.name)
                                        if order.order_status_id != order_status.id:
                                            order.order_status = order_status
                                            order.save()
                                            logger.info(f"[eshopbox] Updated order {order.id} to status {shipment_status}")
                                            try:
                                                trigger_order_status_notifications(company, order_status.id, order.id)
                                            except Exception as e:
                                                print(f"Error triggering order status notification: {e}")
                                                pass 
                            except Exception as e:
                                logger.error(f"[eshopbox] Error updating order {order.id}: {e}")

                    elif vendor_name == 'zoopship' and shipmentData['credential_username']:
                        zoopship_service = ZoopshipService(
                            shipmentData['credential_username'],
                            shipmentData['credential_password']
                        )
                        excluded_statuses = [
                            'ACCEPTED', 'No Response', 'Future Order', 'Non Serviceable',
                            'DELIVERED', 'RTO DELIVERED', 'EXCEPTION',"PENDING"
                        ]
                        orders = Order_Table.objects.filter(
                            order_wayBill__isnull=False,
                            company=company
                        ).exclude(order_wayBill='').exclude(order_status__name__in=excluded_statuses)

                        for order in orders:
                            try:
                                
                                awb_number = order.order_wayBill
                                
                                response = zoopship_service.track_order(awb_number)
                                if not response.get("status"):
                                    continue
                                shipment_status = response.get("data", {}).get("tracking_data", {}).get("status_name") or None

                                # shipment_status = response.get("data", {}).get("status")
                            
                                if shipment_status:
                                    mapped_status = get_main_order_status_for_vendor_status(vendor_id, shipment_status)
                                    if mapped_status:
                                        order_status, _ = OrderStatus.objects.get_or_create(name=mapped_status.name)
                                        if order.order_status_id != order_status.id:
                                            order.order_status = order_status
                                            order.save()
                                            logger.info(f"[zoopship] Updated order {order.id} to status {shipment_status}")
                                            try:
                                                trigger_order_status_notifications(company, order_status.id, order.id)
                                            except Exception as e:
                                                print(f"Error triggering order status notification: {e}")
                                                pass 
                            except Exception as e:
                                logger.error(f"[zoopship] Error updating order {order.id}: {e}")
            except Exception as e:
                logger.error(f"Error fetching shipment details: {e}")


        # Set up the scheduler to periodically call the `fetch_and_update_shipments` function
        scheduler = BackgroundScheduler()
        scheduler.add_job(
            fetch_and_update_shipments,
            IntervalTrigger(minutes=20),  # Run every 20 minutes
            id="fetch_and_update_shipments",
            max_instances=1,
            # misfire_grace_time=30,  # Optional
        )
        scheduler.start()
        logger.info("Scheduler started")
