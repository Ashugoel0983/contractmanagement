"""
Contracts API endpoints for Contract Management System
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc, or_

from app import db
from models import Contract, ContractMetadata, ContractParty, ContractStatus, ContractType
from auth import requires_auth, requires_role, get_user_info

# Set up logging
logger = logging.getLogger(__name__)

# Create blueprint
contracts_bp = Blueprint('contracts', __name__)

@contracts_bp.route('', methods=['GET'])
@requires_auth
def get_contracts():
    """
    Get all contracts with optional filtering
    
    Query params:
        status: Filter by contract status
        type: Filter by contract type
        owner_id: Filter by owner ID
        search: Search in title and description
        tags: Filter by tags (comma-separated)
        sort_by: Field to sort by
        sort_order: asc or desc
        page: Page number (default: 1)
        per_page: Items per page (default: 20)
    """
    try:
        # Get query parameters
        status = request.args.get('status')
        contract_type = request.args.get('type')
        owner_id = request.args.get('owner_id')
        search_query = request.args.get('search')
        tags = request.args.get('tags')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
        
        # Start query
        query = Contract.query
        
        # Apply filters
        if status:
            try:
                status_enum = getattr(ContractStatus, status.upper())
                query = query.filter(Contract.status == status_enum)
            except (AttributeError, ValueError):
                pass
        
        if contract_type:
            try:
                type_enum = getattr(ContractType, contract_type.upper().replace(' ', '_'))
                query = query.filter(Contract.contract_type == type_enum)
            except (AttributeError, ValueError):
                pass
        
        if owner_id:
            query = query.filter(Contract.owner_id == owner_id)
        
        if search_query:
            search_filter = or_(
                Contract.title.ilike(f'%{search_query}%'),
                Contract.description.ilike(f'%{search_query}%'),
                Contract.contract_number.ilike(f'%{search_query}%')
            )
            query = query.filter(search_filter)
        
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                query = query.filter(Contract.tags_json.ilike(f'%{tag.strip()}%'))
        
        # Apply sorting
        if sort_by in ['created_at', 'updated_at', 'title', 'start_date', 'end_date', 'value']:
            sort_column = getattr(Contract, sort_by)
            if sort_order.lower() == 'asc':
                query = query.order_by(sort_column)
            else:
                query = query.order_by(desc(sort_column))
        
        # Apply pagination
        paginated = query.paginate(page=page, per_page=per_page)
        
        # Format results
        contracts = []
        for contract in paginated.items:
            contract_data = contract.to_dict()
            
            # Get contract metadata
            metadata = ContractMetadata.query.filter_by(contract_id=contract.id).first()
            if metadata:
                contract_data['metadata'] = metadata.to_dict()
            
            # Get contract parties
            parties = ContractParty.query.filter_by(contract_id=contract.id).all()
            contract_data['parties'] = [party.to_dict() for party in parties]
            
            contracts.append(contract_data)
        
        # Return results
        return jsonify({
            'success': True,
            'contracts': contracts,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_pages': paginated.pages,
                'total_items': paginated.total
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting contracts: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving contracts: {str(e)}'
        }), 500

@contracts_bp.route('/<int:contract_id>', methods=['GET'])
@requires_auth
def get_contract(contract_id):
    """
    Get a contract by ID
    """
    try:
        # Get contract
        contract = Contract.query.get(contract_id)
        
        if not contract:
            return jsonify({
                'success': False,
                'message': 'Contract not found'
            }), 404
        
        # Get user info
        user_info = get_user_info()
        
        # Check if user has access to contract
        if str(contract.owner_id) != str(user_info.get('sub')) and user_info.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'You do not have permission to access this contract'
            }), 403
        
        # Format contract data
        contract_data = contract.to_dict()
        
        # Get contract metadata
        metadata = ContractMetadata.query.filter_by(contract_id=contract.id).first()
        if metadata:
            contract_data['metadata'] = metadata.to_dict()
        
        # Get contract parties
        parties = ContractParty.query.filter_by(contract_id=contract.id).all()
        contract_data['parties'] = [party.to_dict() for party in parties]
        
        # Return result
        return jsonify({
            'success': True,
            'contract': contract_data
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting contract {contract_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving contract: {str(e)}'
        }), 500

@contracts_bp.route('/<int:contract_id>', methods=['PUT'])
@requires_auth
def update_contract(contract_id):
    """
    Update a contract by ID
    """
    try:
        # Get contract
        contract = Contract.query.get(contract_id)
        
        if not contract:
            return jsonify({
                'success': False,
                'message': 'Contract not found'
            }), 404
        
        # Get user info
        user_info = get_user_info()
        
        # Check if user has access to contract
        if str(contract.owner_id) != str(user_info.get('sub')) and user_info.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'You do not have permission to update this contract'
            }), 403
        
        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'message': 'No data provided'
            }), 400
        
        # Update contract fields
        if 'title' in data:
            contract.title = data['title']
        
        if 'description' in data:
            contract.description = data['description']
        
        if 'contract_type' in data:
            try:
                contract.contract_type = getattr(ContractType, data['contract_type'].upper().replace(' ', '_'))
            except (AttributeError, ValueError):
                return jsonify({
                    'success': False,
                    'message': f'Invalid contract type: {data["contract_type"]}'
                }), 400
        
        if 'status' in data:
            try:
                contract.status = getattr(ContractStatus, data['status'].upper())
            except (AttributeError, ValueError):
                return jsonify({
                    'success': False,
                    'message': f'Invalid contract status: {data["status"]}'
                }), 400
        
        if 'start_date' in data and data['start_date']:
            try:
                contract.start_date = datetime.fromisoformat(data['start_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': f'Invalid start date format: {data["start_date"]}'
                }), 400
        
        if 'end_date' in data and data['end_date']:
            try:
                contract.end_date = datetime.fromisoformat(data['end_date'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return jsonify({
                    'success': False,
                    'message': f'Invalid end date format: {data["end_date"]}'
                }), 400
        
        if 'value' in data:
            contract.value = data['value']
        
        if 'currency' in data:
            contract.currency = data['currency']
        
        if 'payment_terms' in data:
            contract.payment_terms = data['payment_terms']
        
        if 'tags' in data:
            contract.tags = data['tags']
        
        # Update metadata if provided
        if 'metadata' in data:
            metadata = ContractMetadata.query.filter_by(contract_id=contract.id).first()
            
            if not metadata:
                metadata = ContractMetadata()
                metadata.contract_id = contract.id
                db.session.add(metadata)
            
            metadata_data = data['metadata']
            
            if 'invoice_required' in metadata_data:
                metadata.invoice_required = metadata_data['invoice_required']
            
            if 'jurisdiction' in metadata_data:
                metadata.jurisdiction = metadata_data['jurisdiction']
            
            if 'governing_law' in metadata_data:
                metadata.governing_law = metadata_data['governing_law']
            
            if 'dispute_resolution' in metadata_data:
                metadata.dispute_resolution = metadata_data['dispute_resolution']
            
            if 'termination_clause' in metadata_data:
                metadata.termination_clause = metadata_data['termination_clause']
            
            if 'confidentiality_clause' in metadata_data:
                metadata.confidentiality_clause = metadata_data['confidentiality_clause']
            
            if 'limitation_of_liability' in metadata_data:
                metadata.limitation_of_liability = metadata_data['limitation_of_liability']
            
            if 'force_majeure' in metadata_data:
                metadata.force_majeure = metadata_data['force_majeure']
            
            if 'indemnification' in metadata_data:
                metadata.indemnification = metadata_data['indemnification']
        
        # Update parties if provided
        if 'parties' in data:
            for party_data in data['parties']:
                if 'id' in party_data:
                    # Update existing party
                    party = ContractParty.query.get(party_data['id'])
                    
                    if party and party.contract_id == contract.id:
                        if 'party_type' in party_data:
                            party.party_type = party_data['party_type']
                        
                        if 'legal_name' in party_data:
                            party.legal_name = party_data['legal_name']
                        
                        if 'address' in party_data:
                            party.address = party_data['address']
                        
                        if 'contact_person' in party_data:
                            party.contact_person = party_data['contact_person']
                        
                        if 'email' in party_data:
                            party.email = party_data['email']
                        
                        if 'phone' in party_data:
                            party.phone = party_data['phone']
                else:
                    # Create new party
                    party = ContractParty()
                    party.contract_id = contract.id
                    
                    if 'party_type' in party_data:
                        party.party_type = party_data['party_type']
                    else:
                        party.party_type = 'other'
                    
                    if 'legal_name' in party_data:
                        party.legal_name = party_data['legal_name']
                    else:
                        return jsonify({
                            'success': False,
                            'message': 'Legal name is required for new parties'
                        }), 400
                    
                    party.address = party_data.get('address', '')
                    party.contact_person = party_data.get('contact_person', '')
                    party.email = party_data.get('email', '')
                    party.phone = party_data.get('phone', '')
                    
                    db.session.add(party)
        
        # Save changes
        db.session.commit()
        
        # Return updated contract
        return jsonify({
            'success': True,
            'message': 'Contract updated successfully',
            'contract': contract.to_dict()
        }), 200
    
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        
        logger.error(f"Error updating contract {contract_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error updating contract: {str(e)}'
        }), 500

@contracts_bp.route('/<int:contract_id>', methods=['DELETE'])
@requires_auth
def delete_contract(contract_id):
    """
    Delete a contract by ID
    """
    try:
        # Get contract
        contract = Contract.query.get(contract_id)
        
        if not contract:
            return jsonify({
                'success': False,
                'message': 'Contract not found'
            }), 404
        
        # Get user info
        user_info = get_user_info()
        
        # Check if user has permission to delete
        if str(contract.owner_id) != str(user_info.get('sub')) and user_info.get('role') != 'admin':
            return jsonify({
                'success': False,
                'message': 'You do not have permission to delete this contract'
            }), 403
        
        # Check if contract has recurring invoices
        from models import Invoice
        recurring_invoices = Invoice.query.filter_by(
            contract_id=contract.id,
            is_recurring=True
        ).first()
        
        if recurring_invoices:
            return jsonify({
                'success': False,
                'message': 'Cannot delete contract with recurring invoices'
            }), 400
        
        # Delete contract and related data
        db.session.delete(contract)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Contract deleted successfully'
        }), 200
    
    except Exception as e:
        # Rollback on error
        db.session.rollback()
        
        logger.error(f"Error deleting contract {contract_id}: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error deleting contract: {str(e)}'
        }), 500

@contracts_bp.route('/metrics', methods=['GET'])
@requires_auth
def get_contract_metrics():
    """
    Get contract metrics for dashboard
    """
    try:
        # Get user info
        user_info = get_user_info()
        user_id = user_info.get('sub')
        
        # Initialize metrics
        metrics = {
            'total_contracts': 0,
            'active_contracts': 0,
            'expiring_soon': 0,
            'by_status': {},
            'by_type': {},
            'by_month': {}
        }
        
        # Get the user's contracts
        query = Contract.query
        if user_info.get('role') != 'admin':
            query = query.filter(Contract.owner_id == user_id)
        
        # Calculate total contracts
        metrics['total_contracts'] = query.count()
        
        # Calculate active contracts
        metrics['active_contracts'] = query.filter(
            Contract.status == ContractStatus.ACTIVE
        ).count()
        
        # Calculate contracts expiring in 30 days
        from datetime import datetime, timedelta
        thirty_days = datetime.utcnow() + timedelta(days=30)
        metrics['expiring_soon'] = query.filter(
            Contract.end_date.between(datetime.utcnow(), thirty_days)
        ).count()
        
        # Calculate contracts by status
        for status in ContractStatus:
            count = query.filter(Contract.status == status).count()
            metrics['by_status'][status.value] = count
        
        # Calculate contracts by type
        for contract_type in ContractType:
            count = query.filter(Contract.contract_type == contract_type).count()
            metrics['by_type'][contract_type.value] = count
        
        # Calculate contracts by month (creation date)
        from sqlalchemy import func, extract
        month_counts = db.session.query(
            extract('year', Contract.created_at).label('year'),
            extract('month', Contract.created_at).label('month'),
            func.count().label('count')
        )
        
        if user_info.get('role') != 'admin':
            month_counts = month_counts.filter(Contract.owner_id == user_id)
        
        month_counts = month_counts.group_by('year', 'month').all()
        
        for year, month, count in month_counts:
            month_key = f"{int(year)}-{int(month):02d}"
            metrics['by_month'][month_key] = count
        
        return jsonify({
            'success': True,
            'metrics': metrics
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting contract metrics: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error retrieving contract metrics: {str(e)}'
        }), 500