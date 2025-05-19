import logging
from flask import Blueprint, request, jsonify
from sqlalchemy import or_, and_, func
from app import db
from models import Contract, ContractParty, ContractMetadata, User, UserRole, ContractStatus, ContractType
from auth import requires_auth, get_user_info

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)

@search_bp.route('', methods=['GET'])
@requires_auth
def search_contracts():
    """Search contracts with advanced filtering"""
    try:
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Parse query parameters
        query_term = request.args.get('q', '')
        
        # Filters
        contract_type = request.args.get('type')
        status = request.args.get('status')
        party = request.args.get('party')
        owner_id = request.args.get('owner_id')
        min_value = request.args.get('min_value')
        max_value = request.args.get('max_value')
        start_date_after = request.args.get('start_date_after')
        start_date_before = request.args.get('start_date_before')
        end_date_after = request.args.get('end_date_after')
        end_date_before = request.args.get('end_date_before')
        risk_flagged = request.args.get('risk_flagged')
        tags = request.args.get('tags')
        
        # Pagination
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        # Sort options
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Build base query
        query = db.session.query(Contract).distinct()
        
        # Apply search term if provided
        if query_term:
            search_term = f"%{query_term}%"
            query = query.filter(
                or_(
                    Contract.title.ilike(search_term),
                    Contract.description.ilike(search_term),
                    Contract.contract_number.ilike(search_term),
                    Contract.extracted_text.ilike(search_term)
                )
            )
        
        # Apply filters
        if contract_type:
            try:
                query = query.filter(Contract.contract_type == ContractType(contract_type))
            except ValueError:
                pass
        
        if status:
            try:
                query = query.filter(Contract.status == ContractStatus(status))
            except ValueError:
                pass
        
        if party:
            query = query.join(ContractParty).filter(
                ContractParty.legal_name.ilike(f"%{party}%")
            )
        
        if owner_id:
            query = query.filter(Contract.owner_id == owner_id)
        
        if min_value:
            query = query.filter(Contract.value >= float(min_value))
        
        if max_value:
            query = query.filter(Contract.value <= float(max_value))
        
        if start_date_after:
            query = query.filter(Contract.start_date >= start_date_after)
        
        if start_date_before:
            query = query.filter(Contract.start_date <= start_date_before)
        
        if end_date_after:
            query = query.filter(Contract.end_date >= end_date_after)
        
        if end_date_before:
            query = query.filter(Contract.end_date <= end_date_before)
        
        if risk_flagged == 'true':
            query = query.filter(Contract.status == ContractStatus.RISK_FLAGGED)
        
        if tags:
            tag_list = tags.split(',')
            for tag in tag_list:
                query = query.filter(Contract.tags.contains([tag]))
        
        # Role-based access control
        if user.role != UserRole.ADMIN:
            # Non-admins can only see their own contracts
            query = query.filter(Contract.owner_id == user.id)
        
        # Count total results for pagination
        total_count = query.count()
        
        # Apply sorting
        if sort_by == 'value':
            if sort_order == 'asc':
                query = query.order_by(Contract.value.asc())
            else:
                query = query.order_by(Contract.value.desc())
        elif sort_by == 'end_date':
            if sort_order == 'asc':
                query = query.order_by(Contract.end_date.asc())
            else:
                query = query.order_by(Contract.end_date.desc())
        elif sort_by == 'start_date':
            if sort_order == 'asc':
                query = query.order_by(Contract.start_date.asc())
            else:
                query = query.order_by(Contract.start_date.desc())
        elif sort_by == 'title':
            if sort_order == 'asc':
                query = query.order_by(Contract.title.asc())
            else:
                query = query.order_by(Contract.title.desc())
        else:  # Default: created_at
            if sort_order == 'asc':
                query = query.order_by(Contract.created_at.asc())
            else:
                query = query.order_by(Contract.created_at.desc())
        
        # Apply pagination
        contracts = query.limit(limit).offset(offset).all()
        
        # Prepare result
        result = {
            'contracts': [contract.to_dict() for contract in contracts],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset
            },
            'filters': {
                'query': query_term,
                'type': contract_type,
                'status': status,
                'party': party,
                'owner_id': owner_id,
                'value_range': [min_value, max_value] if min_value or max_value else None,
                'start_date_range': [start_date_after, start_date_before] if start_date_after or start_date_before else None,
                'end_date_range': [end_date_after, end_date_before] if end_date_after or end_date_before else None,
                'risk_flagged': risk_flagged == 'true',
                'tags': tags.split(',') if tags else []
            }
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error searching contracts: {str(e)}")
        return jsonify({'error': f"Failed to search contracts: {str(e)}"}), 500

@search_bp.route('/tags', methods=['GET'])
@requires_auth
def get_all_tags():
    """Get all unique tags used in contracts"""
    try:
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Query to get all unique tags
        # This is a simplified approach that works for PostgreSQL
        # In a real implementation, this would need to be adapted for the specific database
        
        # For non-admin users, get tags only from their contracts
        if user.role != UserRole.ADMIN:
            contracts = Contract.query.filter_by(owner_id=user.id).all()
        else:
            contracts = Contract.query.all()
        
        # Extract all tags
        all_tags = []
        for contract in contracts:
            if contract.tags:
                all_tags.extend(contract.tags)
        
        # Get unique tags
        unique_tags = sorted(list(set(all_tags)))
        
        return jsonify({'tags': unique_tags}), 200
        
    except Exception as e:
        logger.error(f"Error getting tags: {str(e)}")
        return jsonify({'error': f"Failed to get tags: {str(e)}"}), 500

@search_bp.route('/filters', methods=['GET'])
@requires_auth
def get_search_filters():
    """Get available search filters with counts"""
    try:
        # Get user info for authorization check
        user_info = get_user_info()
        user = User.query.filter_by(auth0_id=user_info.get('sub')).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Base query for counting
        base_query = db.session.query(Contract)
        
        # Role-based access control
        if user.role != UserRole.ADMIN:
            base_query = base_query.filter(Contract.owner_id == user.id)
        
        # Get contract type counts
        type_counts = {}
        for contract_type in ContractType:
            count = base_query.filter(Contract.contract_type == contract_type).count()
            type_counts[contract_type.value] = count
        
        # Get status counts
        status_counts = {}
        for status in ContractStatus:
            count = base_query.filter(Contract.status == status).count()
            status_counts[status.value] = count
        
        # Get owner counts
        owner_counts = {}
        owners = db.session.query(
            User.id,
            User.name,
            func.count(Contract.id)
        ).join(
            Contract, User.id == Contract.owner_id
        ).group_by(User.id).all()
        
        for owner_id, owner_name, count in owners:
            owner_counts[str(owner_id)] = {
                'name': owner_name,
                'count': count
            }
        
        # Get expiry ranges
        current_month_count = base_query.filter(
            func.extract('month', Contract.end_date) == func.extract('month', func.current_date()),
            func.extract('year', Contract.end_date) == func.extract('year', func.current_date())
        ).count()
        
        next_quarter_count = base_query.filter(
            Contract.end_date > func.current_date(),
            Contract.end_date <= func.current_date() + func.interval('3 months')
        ).count()
        
        expiry_counts = {
            'current_month': current_month_count,
            'next_quarter': next_quarter_count,
            'expired': base_query.filter(Contract.end_date < func.current_date()).count()
        }
        
        # Get value ranges
        value_ranges = {
            'under_10k': base_query.filter(Contract.value < 10000).count(),
            '10k_50k': base_query.filter(Contract.value >= 10000, Contract.value < 50000).count(),
            '50k_100k': base_query.filter(Contract.value >= 50000, Contract.value < 100000).count(),
            'over_100k': base_query.filter(Contract.value >= 100000).count()
        }
        
        result = {
            'types': type_counts,
            'statuses': status_counts,
            'owners': owner_counts,
            'expiry': expiry_counts,
            'value_ranges': value_ranges
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error getting search filters: {str(e)}")
        return jsonify({'error': f"Failed to get search filters: {str(e)}"}), 500
